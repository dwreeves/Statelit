from functools import lru_cache
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar

from pydantic import BaseModel
from pydantic.fields import ModelField
from pydantic.utils import Representation
from streamlit.runtime.state.session_state import SessionState
from typing_extensions import Literal

from statelit.state.base import StatefulObjectBase
from statelit.utils.mro import find_implementation


ST = TypeVar("ST", bound=StatefulObjectBase)


def _identity(v: Any) -> Any:
    return v


class StatelitConverterAssociation(Representation):
    __slots__ = ("converter_name", "callback_type", "fields", "types")

    def __init__(
            self,
            converter_name: str,
            callback_type: Literal["widget", "to_streamlit", "from_streamlit"],
            fields: List[str] = None,
            types: List[type] = None
    ):
        self.converter_name = converter_name
        self.callback_type = callback_type
        if fields and types:
            raise ValueError("Pass only fields or types, not both.")
        self.fields = fields or []
        self.types = types or []


class FieldCallbacks(Representation):
    __slots__ = ("widget_callback", "to_streamlit_callback", "from_streamlit_callback")

    def __init__(
            self,
            widget_callback: callable,
            *,
            to_streamlit_callback: Optional[Callable[[Any], Any]] = None,
            from_streamlit_callback: Optional[Callable[[Any], Any]] = None
    ):
        self.widget_callback = widget_callback
        self.to_streamlit_callback: Callable[[Any], Any] = to_streamlit_callback or _identity
        self.from_streamlit_callback: Callable[[Any], Any] = from_streamlit_callback or _identity


class FieldFactoryBase:
    def __init__(self, key_prefix: str, session_state: SessionState):
        self.key_prefix = key_prefix
        self.session_state = session_state

    def __call__(self, value: Any, field: ModelField, model: Type[BaseModel]) -> ST:
        raise NotImplementedError


class CallbackConverterTypeMeta(type):

    def __instancecheck__(self, instance):
        return bool(
            callable(instance) and hasattr(instance, "__statelit_callback_info__")
        )


class CallbackConverterType(metaclass=CallbackConverterTypeMeta):
    __statelit_callback_info__: List[StatelitConverterAssociation]
    __name__: str

    def __new__(cls, callback_converter: callable):
        callback_converter.__statelit_callback_info__ = []
        return callback_converter

    def __call__(self, value: Any, model: Type[BaseModel], field: ModelField) -> callable:
        raise NotImplementedError


def is_converter_for(
        callback_type: Literal["widget", "to_streamlit", "from_streamlit"],
        *,
        fields: List[str] = None,
        types: List[type] = None
) -> Callable[[callable], CallbackConverterType]:
    def _wrap(func: callable) -> CallbackConverterType:
        if not isinstance(func, CallbackConverterType):
            func = CallbackConverterType(func)
        func.__statelit_callback_info__.append(StatelitConverterAssociation(
            converter_name=func.__name__,
            callback_type=callback_type,
            fields=fields,
            types=types
        ))
        return func

    return _wrap


def is_widget_callback_converter_for(
        fields: List[str] = None,
        types: List[type] = None
) -> Callable[[callable], CallbackConverterType]:
    return is_converter_for(
        "widget",
        fields=fields,
        types=types
    )


def is_from_streamlit_callback_converter_for(
        fields: List[str] = None,
        types: List[type] = None
) -> Callable[[callable], CallbackConverterType]:
    return is_converter_for(
        "from_streamlit",
        fields=fields,
        types=types
    )


def is_to_streamlit_callback_converter_for(
        fields: List[str] = None,
        types: List[type] = None
) -> Callable[[callable], CallbackConverterType]:
    return is_converter_for(
        "to_streamlit",
        fields=fields,
        types=types
    )


class DynamicFieldFactoryBase(FieldFactoryBase):
    statelit_converter_associations: List[StatelitConverterAssociation]

    def __init__(self, key_prefix: str, session_state: SessionState):
        super().__init__(key_prefix=key_prefix, session_state=session_state)
        self.statelit_converter_associations = []
        self._register_converter_callables()

    def _register_converter_callables(self):
        statelit_converter_associations: List[StatelitConverterAssociation] = []
        for attr_name in dir(self):
            obj = getattr(self, attr_name)
            if isinstance(obj, CallbackConverterType):
                for assoc in obj.__statelit_callback_info__:
                    statelit_converter_associations.append(assoc)
        self.statelit_converter_associations = statelit_converter_associations

    @lru_cache(maxsize=None)
    def callback_mapping(
            self,
            *,
            association_type: Literal["fields", "types"],
            callback_type: Literal["widget", "to_streamlit", "from_streamlit"]
    ) -> Dict[Any, callable]:
        d: Dict[str, callable] = {}
        for assoc in self.statelit_converter_associations:
            if assoc.callback_type == callback_type:
                for i in getattr(assoc, association_type):
                    d[i] = getattr(self, assoc.converter_name)
        return d

    def get_callback_by_type(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel],
            callback_type: Literal["widget", "to_streamlit", "from_streamlit"]
    ) -> Optional[callable]:
        if field.name in self.callback_mapping(callback_type=callback_type, association_type="fields"):
            converter = self.callback_mapping(callback_type=callback_type, association_type="fields")[field.name]
        else:
            converter = find_implementation(
                field.type_,
                self.callback_mapping(callback_type=callback_type, association_type="types")
            )
        if converter is not None:
            return converter(value=value, field=field, model=model)
        else:
            return None

    def get_widget_callback(self, value: Any, field: ModelField, model: Type[BaseModel]):
        callback = self.get_callback_by_type(
            value=value,
            field=field,
            model=model,
            callback_type="widget"
        )
        if callback is None:
            raise TypeError(
                f"Could not find a valid Streamlit callback for Field({field})."
                f" Check to make sure that {field.type_!r} is a supported type."
            )
        return callback

    def get_from_streamlit_callback(self, value: Any, field: ModelField, model: Type[BaseModel]):
        return self.get_callback_by_type(
            value=value,
            field=field,
            model=model,
            callback_type="from_streamlit"
        )

    def get_to_streamlit_callback(self, value: Any, field: ModelField, model: Type[BaseModel]):
        return self.get_callback_by_type(
            value=value,
            field=field,
            model=model,
            callback_type="to_streamlit"
        )

    def get_field_callbacks(self, value: Any, field: ModelField, model: Type[BaseModel]) -> FieldCallbacks:
        return FieldCallbacks(
            widget_callback=self.get_widget_callback(value=value, field=field, model=model),
            to_streamlit_callback=self.get_to_streamlit_callback(value=value, field=field, model=model),
            from_streamlit_callback=self.get_from_streamlit_callback(value=value, field=field, model=model)
        )

    def get_object_type(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel],
    ) -> Type[StatefulObjectBase]:
        if issubclass(field.type_, BaseModel):
            from statelit.state.model import StatelitModel
            return StatelitModel
        else:
            from statelit.state.field import StatelitField
            return StatelitField

    def __call__(
            self,
            value: Any,
            field: ModelField,
            model: Type[BaseModel],
    ) -> ST:
        field_callbacks: FieldCallbacks = self.get_field_callbacks(value=value, model=model, field=field)
        base_state_key = f"{self.key_prefix}.{field.name}"
        statelit_field_class = self.get_object_type(value=value, model=model, field=field)
        statelit_field = statelit_field_class(
            value=value,
            name=field.name,
            base_state_key=base_state_key,
            widget_callback=field_callbacks.widget_callback,
            to_streamlit_callback=field_callbacks.to_streamlit_callback,
            from_streamlit_callback=field_callbacks.from_streamlit_callback,
            session_state=self.session_state,
        )
        return statelit_field
