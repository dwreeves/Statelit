import json
import math
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from functools import partial
from functools import wraps
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Type
from typing import Union

import streamlit as st
from pydantic import BaseModel
from pydantic.color import Color
from pydantic.fields import ModelField
from streamlit.runtime.state.session_state import SessionState

from statelit.field_factory.base import DynamicFieldFactoryBase
from statelit.field_factory.base import is_fallback_default_value_converter_for
from statelit.field_factory.base import is_from_streamlit_callback_converter_for
from statelit.field_factory.base import is_to_streamlit_callback_converter_for
from statelit.field_factory.base import is_widget_callback_converter_for
from statelit.json import statelit_encoder
from statelit.types import DateRange
from statelit.utils.mro import find_implementation
from statelit.utils.mro import get_args
from statelit.utils.mro import get_origin
from statelit.utils.mro import lenient_issubclass


def _modify_kwargs_max_and_min(
        kwargs: Dict[str, Any],
        field: ModelField,
        step: Any = 1,
        conv: callable = None
) -> Dict[str, Any]:
    if not conv:
        def conv(x):
            return x
    if get_origin(field.type_) is not None:
        # Assume assume first type is the type for both.
        # (Doesn't make a ton of sense to handle both, since both numbers share streamlit widget kwargs)
        typ = get_args(field.type_)[0]
    else:
        typ = field.type_

    if hasattr(typ, "le") and typ.le is not None:
        kwargs["max_value"] = conv(typ.le)
    if hasattr(typ, "lt") and typ.lt is not None:
        kwargs["max_value"] = conv(typ.lt - step)
    if hasattr(typ, "ge") and typ.ge is not None:
        kwargs["min_value"] = conv(typ.ge)
    if hasattr(typ, "gt") and typ.gt is not None:
        kwargs["min_value"] = conv(typ.gt + step)
    return kwargs


def _modify_kwargs_label(kwargs: Dict[str, Any], field: ModelField) -> Dict[str, Any]:
    if field.field_info.title:
        kwargs["label"] = field.field_info.title
    else:
        kwargs["label"] = field.name
    return kwargs


def _modify_kwargs_help(kwargs: Dict[str, Any], field: ModelField) -> Dict[str, Any]:
    if field.field_info.description:
        kwargs["help"] = field.field_info.description
    return kwargs


def _modify_disabled(kwargs: Dict[str, Any], field: ModelField) -> Dict[str, Any]:
    disabled = field.field_info.extra.get("statelit__disabled")
    if disabled is not None:
        kwargs["disabled"] = disabled
    return kwargs


def _maybe_extract_streamlit_callable(field: ModelField) -> Optional[callable]:
    streamlit_widget = field.field_info.extra.get("statelit__streamlit_widget")
    if streamlit_widget:
        return streamlit_widget

    type_lookup = field.field_info.extra.get("statelit__streamlit_widget_registry")
    if type_lookup:
        return find_implementation(field.type_, type_lookup)

    return None


def _allow_optional(callback: callable, enabled: bool, session_state: SessionState) -> callable:
    @wraps(callback)
    def _wrapper(*args, **kwargs):
        key = kwargs.pop("key", None)
        label = kwargs.get("label", "field")
        on_change = kwargs.get("on_change", lambda: None)

        persisted_value_key = f"{key}._persisted_value"
        checkbox_key = f"{key}._enabled"

        if persisted_value_key not in session_state:
            session_state[persisted_value_key] = session_state[key]

        if checkbox_key not in session_state:
            session_state[checkbox_key] = enabled

        is_enabled = st.checkbox(f"Enable {label}", key=checkbox_key, on_change=on_change)
        widget_return_value = callback(*args, **kwargs, key=persisted_value_key, disabled=(not is_enabled))
        if not is_enabled:
            return_value = session_state[key] = None
        else:
            return_value = session_state[key] = widget_return_value
        on_change()
        return return_value
    return _wrapper


def _redirect_to_persisted_value_key(callback: callable):
    @wraps(callback)
    def _wrapper(*args, **kwargs):
        kwargs["key"] = kwargs.pop("key") + "._persisted_value"
        return callback(*args, **kwargs)
    return _wrapper


class DefaultFieldFactory(DynamicFieldFactoryBase):

    # ==========================================================================
    # Builtin types
    # ==========================================================================

    # TODO: We can set defaults based on constraints, for both simple types and
    #  tuple[T, T] types. However, here I just take the simplest defaults
    #  possible. This is not a huge deal, as it is strongly recommended that a
    #  proper default is set. That said, it would be convenient for some users
    #  to have more magic defaults. Lack of magic defaults can cause errors,
    #  e.g. a ConstrainedInt that does not allow for `0` as a value.

    @is_fallback_default_value_converter_for(types=[int])
    def _default_int(self, **kwargs) -> Callable[[], int]:
        return lambda: 0

    @is_fallback_default_value_converter_for(types=[Tuple[int, int]])
    def _default_int_tuple(self, **kwargs) -> Callable[[], Tuple[int, int]]:
        return lambda: (0, 100)

    @is_fallback_default_value_converter_for(types=[float])
    def _default_float(self, **kwargs) -> Callable[[], float]:
        return lambda: 0.0

    @is_fallback_default_value_converter_for(types=[Tuple[float, float]])
    def _default_float_tuple(self, **kwargs) -> Callable[[], Tuple[float, float]]:
        return lambda: (0.0, 1.0)

    @is_fallback_default_value_converter_for(types=[Decimal])
    def _default_decimal(self, **kwargs) -> Callable[[], Decimal]:
        return lambda: Decimal("0")

    @is_fallback_default_value_converter_for(types=[Tuple[Decimal, Decimal]])
    def _default_decimal_tuple(self, **kwargs) -> Callable[[], Tuple[Decimal, Decimal]]:
        return lambda: (Decimal("0.00"), Decimal("100.00"))

    @is_fallback_default_value_converter_for(types=[list])
    def _default_list(self, **kwargs) -> Callable[[], list]:
        return lambda: []

    @is_fallback_default_value_converter_for(types=[dict])
    def _default_dict(self, **kwargs) -> Callable[[], dict]:
        return lambda: {}

    @is_fallback_default_value_converter_for(types=[str])
    def _default_str(self, **kwargs) -> Callable[[], str]:
        return lambda: ""

    @is_fallback_default_value_converter_for(types=[bool])
    def _default_bool(self, **kwargs) -> Callable[[], bool]:
        return lambda: False

    @is_widget_callback_converter_for(types=[
        int, float, Decimal,
        Tuple[int, int],
        Tuple[float, float],
        Tuple[Decimal, Decimal],
    ])
    def _convert_number(
            self,
            value: Union[int, float, Decimal, tuple],
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        is_tuple = get_origin(field.type_) is not None
        if is_tuple:
            # Assume assume first type is the type for both.
            # (Doesn't make a ton of sense to handle both, since both numbers share streamlit widget kwargs)
            typ = get_args(field.type_)[0]
        else:
            typ = field.type_

        if hasattr(typ, "multiple_of") and typ.multiple_of is not None:
            step = field.type_.multiple_of
        elif lenient_issubclass(typ, float):
            step = 0.01
        elif lenient_issubclass(typ, Decimal):
            if is_tuple and value is not None:
                _v = value[0]
            else:
                _v = value
            if _v is not None:
                step = min(10 ** _v.as_tuple().exponent, 1)
            else:
                step = 1
        else:
            step = 1

        kwargs = {"step": step}

        if not issubclass(typ, int):
            prec = max(0, abs(int(math.log10(step))))
            kwargs["format"] = f"%.{prec}f"

        kwargs = _modify_kwargs_max_and_min(kwargs=kwargs, field=field, step=step, conv=typ)
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
        kwargs = _modify_kwargs_help(kwargs=kwargs, field=field)
        kwargs = _modify_disabled(kwargs=kwargs, field=field)

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        elif ("max_value" in kwargs and "min_value" in kwargs) or is_tuple:
            streamlit_widget = st.slider
        else:
            streamlit_widget = st.number_input

        callback = partial(streamlit_widget, **kwargs)
        if field.allow_none:
            callback = _allow_optional(
                callback,
                enabled=(not kwargs.get("disabled", field.default is None)),
                session_state=self.session_state
            )
        return callback

    @is_to_streamlit_callback_converter_for(types=[list, dict, set])
    def _pre_convert_list_or_dict_or_set(
            self,
            value: int,
            field: ModelField,
            model: Type[BaseModel]
    ):
        def _convert(x):
            return model.__config__.json_dumps(
                x,
                # indent=2,  # TODO: Figure out how to parametrize this
                default=statelit_encoder,
            )

        return _convert

    @is_widget_callback_converter_for(types=[list, dict, set])
    def _convert_list_or_dict_or_set(
            self,
            value: int,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        kwargs = {}
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
        kwargs = _modify_kwargs_help(kwargs=kwargs, field=field)
        kwargs = _modify_disabled(kwargs=kwargs, field=field)

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.text_area

        callback = partial(streamlit_widget, **kwargs)
        if field.allow_none:
            callback = _allow_optional(
                callback,
                enabled=(not kwargs.get("disabled", field.default is None)),
                session_state=self.session_state
            )
        return callback

    @is_from_streamlit_callback_converter_for(types=[list, dict, set])
    def _post_convert_list_or_dict_or_set(
            self,
            value: int,
            field: ModelField,
            model: Type[BaseModel]
    ):
        def _callback(x):
            if field.allow_none and x is None:
                return None
            if isinstance(x, (list, dict, set)):
                return x
            return json.loads(x)
        return _callback

    @is_widget_callback_converter_for(types=[str])
    def _convert_string(
            self,
            value: str,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        kwargs = {}
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
        kwargs = _modify_kwargs_help(kwargs=kwargs, field=field)
        kwargs = _modify_disabled(kwargs=kwargs, field=field)

        if field.field_info.max_length is not None:
            kwargs["max_chars"] = field.field_info.max_length

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        elif field.default is not None and "\n" in field.default:
            streamlit_widget = st.text_area
        else:
            streamlit_widget = st.text_input

        callback = partial(streamlit_widget, **kwargs)
        if field.allow_none:
            callback = _allow_optional(
                callback,
                enabled=(not kwargs.get("disabled", field.default is None)),
                session_state=self.session_state
            )
        return callback

    @is_widget_callback_converter_for(types=[bool])
    def _convert_bool(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        kwargs = {}
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
        kwargs = _modify_kwargs_help(kwargs=kwargs, field=field)
        kwargs = _modify_disabled(kwargs=kwargs, field=field)

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.checkbox

        callback = partial(streamlit_widget, **kwargs)
        if field.allow_none:
            callback = _allow_optional(
                callback,
                enabled=(not kwargs.get("disabled", field.default is None)),
                session_state=self.session_state
            )
        return callback

    @is_to_streamlit_callback_converter_for(types=[Dict[Any, bool], Set[Enum]])
    def _override_pre_convert_to_identity_func(
            self,
            value: int,
            field: ModelField,
            model: Type[BaseModel]
    ):
        # Usually dict and sets serialized to a string.
        # In the special cases of Dict[Any, bool] use f(x)=x.
        # (Note: this is for the multiselect stuff.)
        return lambda x: x

    @is_to_streamlit_callback_converter_for(types=[Set[Enum]])
    def _pre_convert_set_of_enums(
            self,
            value: int,
            field: ModelField,
            model: Type[BaseModel]
    ):
        # Maybe should be opening an issue in Streamlit repo here.
        # But the killer line in multiselect.py is: `default_values = [default_values]`
        # So instead, convert to list.
        def _callback(x):
            if field.allow_none and x is None:
                return None
            return list(x)
        return _callback

    @is_widget_callback_converter_for(types=[Dict[Any, bool]])
    def _convert_dict_of_bool_values(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        kwargs = {}
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
        kwargs = _modify_kwargs_help(kwargs=kwargs, field=field)
        kwargs = _modify_disabled(kwargs=kwargs, field=field)

        def _callback(**kw):
            key = kw.pop("key")
            on_change = kw.pop("on_change", lambda: None)
            data: Dict[Any, bool] = self.session_state[key]

            stable_value_key = key + "._stable_value"

            if self.session_state[key] is not None and stable_value_key not in self.session_state:
                # Pretend to be immutable
                self.session_state[stable_value_key] = list(k for k, v in data.items() if v)

            output = st.multiselect(
                **kw,
                options=list(data),
                default=self.session_state[stable_value_key]
            )
            for k in data:
                data[k] = k in output
            self.session_state[key] = data
            on_change()
            return output

        callback = partial(_callback, **kwargs)
        if field.allow_none:
            callback = _allow_optional(
                callback,
                enabled=(not kwargs.get("disabled", field.default is None)),
                session_state=self.session_state
            )
        return callback

    @is_widget_callback_converter_for(types=[Set[Enum]])
    def _convert_set_of_enums(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        kwargs = {}
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
        kwargs = _modify_kwargs_help(kwargs=kwargs, field=field)
        kwargs = _modify_disabled(kwargs=kwargs, field=field)

        options = [i.value for i in field.type_.__members__.values()]

        def format_func(x):
            return {v.value: k for k, v in field.type_.__members__.items()}.get(x)

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.multiselect

        callback = partial(streamlit_widget, options=options, format_func=format_func, **kwargs)
        if field.allow_none:
            callback = _allow_optional(
                callback,
                enabled=(not kwargs.get("disabled", field.default is None)),
                session_state=self.session_state
            )
        return callback

    # ==========================================================================
    # Core library and Pydantic types
    # ==========================================================================

    @is_fallback_default_value_converter_for(types=[date])
    def _default_date(self, **kwargs) -> Callable[[], date]:
        return date.today

    @is_fallback_default_value_converter_for(types=[datetime])
    def _default_datetime(self, **kwargs) -> Callable[[], datetime]:
        return datetime.utcnow

    @is_fallback_default_value_converter_for(types=[time])
    def _default_time(self, **kwargs) -> Callable[[], time]:
        return lambda: datetime.utcnow().time()

    @is_fallback_default_value_converter_for(types=[Enum])
    def _default_enum(
            self,
            value: None,
            field: ModelField,
            model: Type[BaseModel]
    ) -> Callable[[], Enum]:
        return lambda: getattr(field.type_, next(iter(field.type_.__members__)))

    @is_fallback_default_value_converter_for(types=[BaseModel])
    def _default_base_model(
            self,
            value: None,
            field: ModelField,
            model: Type[BaseModel]
    ) -> Callable[[], Enum]:
        return field.type_

    @is_fallback_default_value_converter_for(types=[Color])
    def _default_color(self, **kwargs) -> Callable[[], Color]:
        return lambda: Color("#000000")

    @is_widget_callback_converter_for(types=[date, datetime])
    def _convert_date(
            self,
            value: Union[date, datetime],
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        kwargs = {}
        kwargs = _modify_kwargs_max_and_min(kwargs=kwargs, field=field, step=timedelta(days=1))
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
        kwargs = _modify_kwargs_help(kwargs=kwargs, field=field)
        kwargs = _modify_disabled(kwargs=kwargs, field=field)

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.date_input

        callback = partial(streamlit_widget, **kwargs)
        if field.allow_none:
            callback = _allow_optional(
                callback,
                enabled=(not kwargs.get("disabled", field.default is None)),
                session_state=self.session_state
            )
        return callback

    @is_widget_callback_converter_for(types=[time])
    def _convert_time(
            self,
            value: Union[date, datetime],
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        kwargs = {}
        kwargs = _modify_kwargs_max_and_min(kwargs=kwargs, field=field, step=timedelta(seconds=1))
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
        kwargs = _modify_kwargs_help(kwargs=kwargs, field=field)
        kwargs = _modify_disabled(kwargs=kwargs, field=field)

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.time_input

        callback = partial(streamlit_widget, **kwargs)
        if field.allow_none:
            callback = _allow_optional(
                callback,
                enabled=(not kwargs.get("disabled", field.default is None)),
                session_state=self.session_state
            )
        return callback

    @is_to_streamlit_callback_converter_for(types=[datetime])
    def _pre_convert_datetime(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        def _callback(x) -> datetime:
            if field.allow_none and x is None:
                return None
            if isinstance(x, datetime):
                return datetime.combine(x.date(), datetime.min.time())
            else:
                return x
        return _callback

    @is_from_streamlit_callback_converter_for(types=[datetime])
    def _post_convert_datetime(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        def _callback(x) -> datetime:
            if field.allow_none and x is None:
                return None
            if isinstance(x, date):
                return datetime.combine(x, datetime.min.time())
            else:
                return x
        return _callback

    @is_widget_callback_converter_for(types=[Enum])
    def _convert_enum(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        kwargs = {}
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
        kwargs = _modify_kwargs_help(kwargs=kwargs, field=field)
        kwargs = _modify_disabled(kwargs=kwargs, field=field)

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.selectbox

        options = [i.value for i in field.type_.__members__.values()]

        def format_func(x):
            return {v.value: k for k, v in field.type_.__members__.items()}.get(x)

        callback = partial(streamlit_widget, options=options, format_func=format_func, **kwargs)
        if field.allow_none:
            callback = _allow_optional(
                callback,
                enabled=(not kwargs.get("disabled", field.default is None)),
                session_state=self.session_state
            )
        return callback

    @is_widget_callback_converter_for(types=[BaseModel])
    def _convert_base_model(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        kwargs = {}
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
        kwargs = _modify_kwargs_help(kwargs=kwargs, field=field)
        kwargs = _modify_disabled(kwargs=kwargs, field=field)

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.text_area

        callback = partial(streamlit_widget, **kwargs)
        if field.allow_none:
            callback = _allow_optional(
                callback,
                enabled=(not kwargs.get("disabled", field.default is None)),
                session_state=self.session_state
            )
        return callback

    @is_to_streamlit_callback_converter_for(types=[BaseModel])
    def _pre_base_model(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        def _callback(x):
            if field.allow_none and x is None:
                return None
            return field.type_.__config__.json_dumps(x, default=statelit_encoder)
        return _callback

    @is_from_streamlit_callback_converter_for(types=[BaseModel])
    def _post_base_model(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        def _callback(x):
            if field.allow_none and (x is None or x == ""):
                return None
            return field.type_.parse_raw(x)
        return _callback

    @is_widget_callback_converter_for(types=[Color])
    def _convert_color(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        kwargs = {}
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
        kwargs = _modify_kwargs_help(kwargs=kwargs, field=field)
        kwargs = _modify_disabled(kwargs=kwargs, field=field)

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.color_picker

        callback = partial(streamlit_widget, **kwargs)
        if field.allow_none:
            callback = _allow_optional(
                callback,
                enabled=(not kwargs.get("disabled", field.default is None)),
                session_state=self.session_state
            )
        return callback

    @is_to_streamlit_callback_converter_for(types=[Color])
    def _pre_convert_color(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> Callable[[Any], Any]:
        def _callback(x) -> str:
            if field.allow_none and x is None:
                return None
            if not isinstance(x, Color):
                return Color(value=x).as_hex()
            return x.as_hex()
        return _callback

    # ==========================================================================
    # Custom Statelit types
    # ==========================================================================

    @is_fallback_default_value_converter_for(types=[DateRange, Tuple[date, date]])
    def _default_color(self, **kwargs) -> Callable[[], DateRange]:
        return lambda: DateRange(lower=date.today() - timedelta(days=1), upper=date.today())

    @is_widget_callback_converter_for(types=[DateRange, Tuple[date, date]])
    def _convert_date_range(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        kwargs = {}
        kwargs = _modify_kwargs_max_and_min(kwargs=kwargs, field=field, step=timedelta(days=1))
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)

        def remapped_keys(**kw):
            # Unfortunately key=? does not work with a date range for st.date_input
            # So we need to hack our way around it.
            #
            # Yes, this is extremely hacky. I know. Help me make it better? :)

            key = kw.pop("key")

            # TODO: Fix this??? `.persisted_value` refers to nothing. (Why does it still work???)
            if key.endswith(".persisted_value"):
                key = ".".join(key.split(".")[:-1])

            stable_value_key = key + "._stable_value"

            if self.session_state[key] is not None and stable_value_key not in self.session_state:
                # Pretend to be immutable
                self.session_state[stable_value_key] = DateRange.convert_to_streamlit(
                    self.session_state[key],
                    field=field,
                    config=field.model_config,
                    upper_is_optional=False
                )

            out = st.date_input(**kw, value=self.session_state[stable_value_key])
            if out != self.session_state[key]:
                if lenient_issubclass(field.type_, DateRange) or (len(out) == 2 and out[1] is not None):
                    self.session_state[key] = out
                    on_change = kw.pop("on_change", lambda: None)
                    on_change()

                else:
                    pass
            elif lenient_issubclass(field.type_, DateRange):
                self.session_state[key] = out
            else:
                pass
            return out

        callback = partial(remapped_keys, **kwargs)
        if field.allow_none:
            callback = _allow_optional(
                callback,
                enabled=(not kwargs.get("disabled", field.default is None)),
                session_state=self.session_state
            )
        return callback

    @is_to_streamlit_callback_converter_for(types=[DateRange, Tuple[date, date]])
    def _pre_date_range(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        def _callback(x):
            if field.allow_none and x is None:
                return None
            return DateRange.validate(x, field=field, config=field.model_config)
        return _callback

    @is_from_streamlit_callback_converter_for(types=[DateRange, Tuple[date, date]])
    def _post_date_range(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        def _callback(x):
            if field.allow_none and x is None:
                return None
            return DateRange.validate(x, field=field, config=field.model_config)
        return _callback
