from functools import partial
from typing import Any
from typing import Generic
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union
from typing import overload

import streamlit as st
from pydantic import BaseModel
from pydantic import ValidationError
from streamlit.runtime.state.session_state import SessionState
from typing_extensions import Literal

from statelit.state.base import StatefulObjectBase
from statelit.state.model import StatelitModel
from statelit.utils.misc import chain_two_callables


ModelInstanceType = TypeVar("ModelInstanceType", bound=BaseModel)
T = TypeVar("T")


class StateManager(Generic[ModelInstanceType]):
    statelit_model_class: Type[StatelitModel] = StatelitModel
    statelit_model: StatelitModel
    session_state: SessionState
    error_message_emoji: str = "🙀"

    def __init__(
            self,
            pydantic_model: Type[ModelInstanceType],
            *,
            session_state: SessionState = None,
            base_state_key: str = None,
    ):
        if base_state_key is None:
            base_state_key = f"statelit.{pydantic_model.__name__}"
        if session_state is None:
            session_state = st.session_state

        if base_state_key in session_state:
            pydantic_obj = pydantic_model.parse_raw(session_state[base_state_key])
        else:
            pydantic_obj = pydantic_model()

        self.statelit_model = self.statelit_model_class(
            value=pydantic_obj,
            base_state_key=base_state_key,
            session_state=session_state
        )

    @property
    def session_state(self) -> SessionState:
        return self.statelit_model.session_state

    @property
    def base_state_key(self) -> str:
        return self.statelit_model.base_state_key

    @property
    def pydantic_obj(self) -> ModelInstanceType:
        return self.statelit_model.value

    @pydantic_obj.setter
    def pydantic_obj(self, v: Any):
        self.statelit_model.value = v

    def sync(self, update_lazy: bool = True):
        self.statelit_model.sync(update_lazy=update_lazy)

    def apply_session_state_delta(self, key: str, parent: StatelitModel):
        if key in parent.all_keys_generator:
            self.apply_obj_delta(key=key, parent=parent)
        for field_name, statelit_field in parent.fields.items():
            if key in statelit_field.all_keys_generator:
                self.apply_field_delta(key, field_name, parent=parent)

    def apply_field_delta(self, key: str, field_name: str, parent: StatelitModel):
        data = {}
        original = parent.value
        try:
            for fn, field in parent.fields.items():
                if fn == field_name:
                    data[fn] = field.from_streamlit(parent.session_state[key])
                else:
                    data[fn] = field.from_streamlit(parent.session_state[field.base_state_key])
            pydantic_obj = parent.value.__class__(**data)
            parent.value = pydantic_obj
        except Exception as e:
            st.error(e, icon=self.error_message_emoji)
            parent.value = original

    def apply_obj_delta(self, key: str, parent: StatelitModel):
        original = parent.value
        try:
            raw_json: str = parent.session_state[key]
            pydantic_obj = parent.from_streamlit(raw_json)
            parent.value = pydantic_obj
        except ValidationError as e:
            st.error(e, icon=self.error_message_emoji)
            parent.value = original

    def _widget(
            self,
            obj: StatefulObjectBase,
            key_suffix: Optional[str] = None,
            validate_output: bool = True,
            **kwargs
    ):
        if "key" in kwargs and key_suffix is not None:
            raise ValueError("key= and key_suffix= kwargs cannot both be set at the same time.")

        if "key" in kwargs:
            key = kwargs.pop("key")
        else:
            key = obj.gen_key(key_suffix=key_suffix)

        if "label" not in kwargs and obj.name is not None:
            kwargs["label"] = obj.name

        obj.commit_key(key=key, state_type="replicated")

        apply_delta = partial(self.apply_session_state_delta, key=key, parent=obj.parent or obj)

        if "on_change" in kwargs:
            apply_delta = chain_two_callables(apply_delta, kwargs.pop("on_change"))

        value = obj.widget(
            on_change=apply_delta,
            key=key,
            **kwargs,
        )

        try:
            if validate_output:
                value = obj.from_streamlit(value)
        except Exception as e:
            st.error(e, icon=self.error_message_emoji)

        return value

    def widget(
            self,
            field_name: str,
            *,
            key_suffix: Optional[str] = None,
            validate_output: bool = True,
            **kwargs
    ) -> Any:
        obj = self.statelit_model.fields[field_name]

        return self._widget(
            obj,
            key_suffix=key_suffix,
            validate_output=validate_output,
            **kwargs
        )

    def _form(
            self,
            statelit_model: StatelitModel,
            key_suffix: Optional[str] = None,
            exclude: List[str] = None,
            flatten: bool = False,
            _header_level: str = "##"
    ):
        for field_name, field in statelit_model.fields.items():
            if field_name not in exclude:
                if flatten and isinstance(field, StatelitModel):
                    _new_exclude = [
                        ".".join(i.split(".")[1:])
                        for i in exclude
                        if i.startswith(f"{field_name}.")
                    ]
                    st.markdown(f"{_header_level} {field.name}")
                    self._form(
                        statelit_model=field,
                        key_suffix=key_suffix,
                        exclude=_new_exclude,
                        flatten=flatten,
                        _header_level=(_header_level + "#")[:6],
                    )
                else:
                    self._widget(field, key_suffix=key_suffix)

    def form(
            self,
            key_suffix: Optional[str] = None,
            exclude: Optional[List[str]] = None,
            flatten: bool = False
    ) -> ModelInstanceType:
        if not exclude:
            exclude = []
        self._form(
            statelit_model=self.statelit_model,
            key_suffix=key_suffix,
            exclude=exclude,
            flatten=flatten
        )
        return self.pydantic_obj

    def code(self) -> str:
        value = self.session_state[self.base_state_key]
        st.code(value, language="json")
        return value

    @overload
    def text_area(
            self, *, key_suffix: str = None, validate_output: Literal[True], **kwargs
    ) -> ModelInstanceType:
        ...

    @overload
    def text_area(
            self, *, key_suffix: str = None, validate_output: Literal[False], **kwargs
    ) -> str:
        ...

    @overload
    def text_area(
            self, *, key_suffix: str = None, validate_output: bool = True, **kwargs
    ) -> ModelInstanceType:
        ...

    def text_area(
            self, *, key_suffix: str = None, validate_output: bool = True, **kwargs
    ) -> Union[ModelInstanceType, str]:
        return self._widget(
            self.statelit_model,
            key_suffix=key_suffix,
            validate_output=validate_output,
            **kwargs
        )

    def lazy_text_area(self, key_suffix: str = None, **kwargs):
        if "key" in kwargs and key_suffix is not None:
            raise ValueError("key= and key_suffix= kwargs cannot both be set at the same time.")

        if "key" in kwargs:
            key = kwargs.pop("key")
        else:
            key = self.statelit_model.gen_key(key_suffix=key_suffix)

        self.statelit_model.commit_key(key=key, state_type="lazy")

        if "label" not in kwargs:
            kwargs["label"] = self.statelit_model.value.__class__.__name__

        def apply_delta():
            try:
                self.statelit_model.value = self.statelit_model.value.parse_raw(self.session_state[key])
                self.session_state[key] = self.session_state[self.base_state_key]
            except ValidationError as e:
                st.error(e, icon=self.error_message_emoji)

        if "on_click" in kwargs:
            apply_delta = chain_two_callables(apply_delta, kwargs.pop("on_click"))

        s = st.text_area(
            key=key,
            **kwargs
        )

        st.button("Apply", on_click=apply_delta, key=f"{key}._button")
        return s
