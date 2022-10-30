from inspect import cleandoc
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar

import streamlit as st
from pydantic import BaseModel
from streamlit.runtime.state.session_state import SessionState

from statelit.field_factory.base import FieldFactoryBase
from statelit.field_factory.main import DefaultFieldFactory
from statelit.json import statelit_encoder
from statelit.state.base import StatefulObjectBase
from statelit.state.field import StatelitField


ModelInstanceType = TypeVar("ModelInstanceType", bound=BaseModel)


class StatelitModel(StatefulObjectBase[ModelInstanceType]):
    field_factory_class: Type[FieldFactoryBase] = DefaultFieldFactory
    field_factory: FieldFactoryBase
    fields: Dict[str, StatelitField]

    json_indent_size: int = 2
    json_default_encoder: Callable[[Any], Any] = statelit_encoder

    def __init__(
            self,
            value: ModelInstanceType,
            *,
            name: str = None,
            base_state_key: str = None,
            replicated_state_keys: Optional[List[str]] = None,
            lazy_state_keys: Optional[List[str]] = None,
            widget_callback: Optional[Callable[..., Any]] = None,
            to_streamlit_callback: Optional[Callable[[Any], Any]] = None,
            from_streamlit_callback: Optional[Callable[[Any], Any]] = None,
            session_state: SessionState = None,
    ):
        if base_state_key is None:
            base_state_key = f"statelit.{value.__class__.__name__}"

        super().__init__(
            value=value,
            name=name if name is not None else value.__class__.__name__,
            base_state_key=base_state_key,
            replicated_state_keys=replicated_state_keys,
            lazy_state_keys=lazy_state_keys,
            widget_callback=widget_callback,
            to_streamlit_callback=to_streamlit_callback,
            from_streamlit_callback=from_streamlit_callback,
            session_state=session_state,
        )
        self.field_factory = self.field_factory_class(
            key_prefix=self.base_state_key,
            session_state=self.session_state
        )

        self.construct_all_statelit_fields()

    def widget(self, **kwargs):
        help_text = cleandoc(self.value.__doc__ or "")
        if help_text:
            kwargs.setdefault("help", help_text)
        kwargs.setdefault("label", self.name)
        return st.text_area(**kwargs)

    def to_streamlit(self, v: ModelInstanceType) -> str:
        return self.value.__config__.json_dumps(
            v,
            indent=self.json_indent_size,
            default=statelit_encoder,
        )

    def from_streamlit(self, v: str) -> ModelInstanceType:
        return self.value.parse_raw(v)

    def construct_all_statelit_fields(self) -> Dict[str, StatelitField]:
        fields_dict: Dict[str, StatelitField] = {}
        for field_name in self.value.__fields__:
            value = getattr(self.value, field_name)
            model = self.value.__class__
            field = self.value.__fields__[field_name]
            fields_dict[field.name] = self.field_factory(value=value, field=field, model=model)
        self.fields = fields_dict

    def sync(self, update_lazy: bool = False):
        super().sync(update_lazy=update_lazy)
        for field_name, field in self.fields.items():
            field.value = getattr(self.value, field_name)
