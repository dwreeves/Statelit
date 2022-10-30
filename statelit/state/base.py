import logging
from typing import Any
from typing import Callable
from typing import Generic
from typing import Iterable
from typing import List
from typing import Optional
from typing import TypeVar
from typing import Union

import streamlit as st
from streamlit.runtime.state.session_state import SessionState
from typing_extensions import Literal


__all__ = ["StatefulObjectBase"]


log = logging.getLogger(__name__)


T = TypeVar("T")


class StatefulObjectBase(Generic[T]):
    _value: T
    base_state_key: str
    replicated_state_keys: List[str]
    lazy_state_keys: List[str]
    session_state: Union[SessionState, SessionState]

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self._value!r}, base_state_key={self.base_state_key!r})"

    def __init__(
            self,
            value: T,
            *,
            name: str = None,
            base_state_key: str,
            replicated_state_keys: Optional[List[str]] = None,
            lazy_state_keys: Optional[List[str]] = None,
            widget_callback: Optional[Callable[..., Any]] = None,
            to_streamlit_callback: Optional[Callable[[Any], Any]] = None,
            from_streamlit_callback: Optional[Callable[[Any], Any]] = None,
            session_state: SessionState = None,
    ):
        self.name = name
        self.base_state_key = base_state_key
        self.replicated_state_keys = replicated_state_keys or []
        self.lazy_state_keys = lazy_state_keys or []

        if widget_callback is not None:
            self.widget = widget_callback

        if to_streamlit_callback is not None:
            self.to_streamlit = to_streamlit_callback

        if from_streamlit_callback is not None:
            self.from_streamlit = from_streamlit_callback

        if session_state is None:
            session_state = st.session_state
        self.session_state = session_state

        self._value = value
        if self.base_state_key not in self.session_state:
            self.session_state[self.base_state_key] = self.to_streamlit(value)

    def from_streamlit(self, v: Any) -> Any:
        return v

    def to_streamlit(self, v: Any) -> Any:
        return v

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, v: T) -> None:
        self._value = self.session_state[self.base_state_key] = v
        self.sync(update_lazy=True)

    def commit_key(
            self,
            key: str,
            *,
            state_type: Literal["base", "replicated", "lazy"] = "replicated"
    ) -> None:
        if state_type == "base":
            self.base_state_key = key
        elif state_type == "replicated":
            self.replicated_state_keys.append(key)
            self.session_state[key] = self.session_state[self.base_state_key]
        elif state_type == "lazy":
            self.lazy_state_keys.append(key)
            if key not in self.session_state:
                self.session_state[key] = self.session_state[self.base_state_key]
        else:
            raise ValueError

    @property
    def all_keys_generator(self) -> Iterable[str]:
        yield self.base_state_key
        for key in self.replicated_state_keys:
            yield key
        for key in self.lazy_state_keys:
            yield key

    def next_key(self) -> str:
        key_list = set(self.all_keys_generator)
        for i in range(100_000):
            candidate_key = f"{self.base_state_key}.{i}"
            if candidate_key not in key_list:
                return candidate_key
        else:
            raise ValueError

    def sync(self, update_lazy: bool = True):
        validated_value = self.to_streamlit(self.value)

        # log.debug(f"Syncing {self} with value {validated_value} and update_lazy={update_lazy}")
        log.debug(f"Syncing {self} with value {validated_value} and update_lazy={update_lazy}")

        for key in [self.base_state_key] + self.replicated_state_keys:
            self.session_state[key] = validated_value
        if update_lazy:
            for key in self.lazy_state_keys:
                self.session_state[key] = validated_value

    def gen_key(self, key_suffix: Optional[str] = None) -> str:
        """Stateless operation"""
        if not key_suffix:
            return self.next_key()
        else:
            return f"{self.base_state_key}.{key_suffix}"
