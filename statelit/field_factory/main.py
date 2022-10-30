from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from enum import Enum
from functools import partial
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Type
from typing import Union

import streamlit as st
from pydantic import BaseModel
from pydantic.color import Color
from pydantic.fields import ModelField

from statelit.field_factory.base import DynamicFieldFactoryBase
from statelit.field_factory.base import is_from_streamlit_callback_converter_for
from statelit.field_factory.base import is_to_streamlit_callback_converter_for
from statelit.field_factory.base import is_widget_callback_converter_for
from statelit.json import statelit_encoder
from statelit.utils.mro import find_implementation


def _modify_kwargs_max_and_min(
        kwargs: Dict[str, Any],
        field: ModelField,
        step: Any = 1,
        conv: callable = None
) -> Dict[str, Any]:
    if not conv:
        def conv(x):
            return x
    if hasattr(field.type_, "le") and field.type_.le is not None:
        kwargs["max_value"] = conv(field.type_.le)
    if hasattr(field.type_, "lt") and field.type_.lt is not None:
        kwargs["max_value"] = conv(field.type_.lt - step)
    if hasattr(field.type_, "ge") and field.type_.ge is not None:
        kwargs["min_value"] = conv(field.type_.ge)
    if hasattr(field.type_, "gt") and field.type_.gt is not None:
        kwargs["min_value"] = conv(field.type_.gt + step)
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


def _maybe_extract_streamlit_callable(field: ModelField) -> Optional[callable]:
    streamlit_widget = field.field_info.extra.get("streamlit_widget")
    if streamlit_widget:
        return streamlit_widget

    type_lookup = field.field_info.extra.get("streamlit_widget_registry")
    if type_lookup:
        return find_implementation(field.type_, type_lookup)

    return None


class DefaultFieldFactory(DynamicFieldFactoryBase):

    # ==========================================================================
    # Builtin types
    # ==========================================================================

    @is_widget_callback_converter_for(types=[int, float])
    def _convert_number(
            self,
            value: int,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        if hasattr(field.type_, "multiple_of") and field.type_.multiple_of is not None:
            step = field.type_.multiple_of
        elif issubclass(field.type_, float):
            step = 0.01
        else:
            step = 1
        kwargs = {"step": step}
        kwargs = _modify_kwargs_max_and_min(kwargs=kwargs, field=field, step=step, conv=field.type_)
        kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
        kwargs = _modify_kwargs_help(kwargs=kwargs, field=field)

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        elif "max_value" in kwargs and "min_value" in kwargs:
            streamlit_widget = st.slider
        else:
            streamlit_widget = st.number_input

        return partial(
            streamlit_widget,
            **kwargs
        )

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

        if field.field_info.max_length is not None:
            kwargs["max_chars"] = field.field_info.max_length

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        elif field.default is not None and "\n" in field.default:
            streamlit_widget = st.text_area
        else:
            streamlit_widget = st.text_input

        return partial(
            streamlit_widget,
            **kwargs
        )

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

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.checkbox

        return partial(
            streamlit_widget,
            **kwargs
        )

    # ==========================================================================
    # Core library and Pydantic types
    # ==========================================================================

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

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.date_input

        return partial(
            streamlit_widget,
            **kwargs
        )

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

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.time_input

        return partial(
            streamlit_widget,
            **kwargs
        )

    @is_to_streamlit_callback_converter_for(types=[datetime])
    def _pre_convert_datetime(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        def _callback(x) -> datetime:
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

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.selectbox

        options = [i.value for i in field.type_.__members__.values()]

        def format_func(x):
            return {v.value: k for k, v in field.type_.__members__.items()}.get(x)

        return partial(
            streamlit_widget,
            options=options,
            format_func=format_func,
            **kwargs
        )

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

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.text_area

        return partial(
            streamlit_widget,
            **kwargs
        )

    @is_to_streamlit_callback_converter_for(types=[BaseModel])
    def _pre_base_model(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        return partial(field.type_.__config__.json_dumps, default=statelit_encoder)

    @is_from_streamlit_callback_converter_for(types=[BaseModel])
    def _post_base_model(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> callable:
        return field.type_.parse_raw

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

        streamlit_widget = _maybe_extract_streamlit_callable(field=field)

        if streamlit_widget:
            pass
        else:
            streamlit_widget = st.color_picker

        return partial(
            streamlit_widget,
            **kwargs
        )

    @is_to_streamlit_callback_converter_for(types=[Color])
    def _pre_convert_color(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel]
    ) -> Callable[[Any], Any]:
        def _callback(x) -> str:
            if not isinstance(x, Color):
                return Color(value=x).as_hex()
            return x.as_hex()
        return _callback

    # ==========================================================================
    # Custom Statelit types
    # ==========================================================================

    # @is_streamlit_callback_converter_for(types=[DateRange])
    # def _convert_date_range(
    #         self,
    #         value: DateRange,
    #         field: ModelField,
    #         model: Type[BaseModel]
    # ) -> callable:
    #     kwargs = {}
    #     kwargs = _modify_kwargs_max_and_min(kwargs=kwargs, field=field, step=timedelta(days=1))
    #     kwargs = _modify_kwargs_label(kwargs=kwargs, field=field)
    #
    #     if value[1] is None:
    #         value = (parse_date(value.lower), )
    #     else:
    #         value = (parse_date(value.lower), parse_date(value.upper))
    #
    #     return partial(
    #         st.date_input,
    #         **kwargs
    #     )
