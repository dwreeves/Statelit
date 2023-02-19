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
    _initial_value: T
    # _enabled: bool

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self._value!r}, base_state_key={self.base_state_key!r})"

    def __init__(
            self,
            value: T,
            *,
            name: str = None,
            enabled: bool = True,
            parent: Optional["StatefulObjectBase"] = None,
            base_state_key: str,
            replicated_state_keys: Optional[List[str]] = None,
            lazy_state_keys: Optional[List[str]] = None,
            widget_callback: Optional[Callable[..., Any]] = None,
            to_streamlit_callback: Optional[Callable[[Any], Any]] = None,
            from_streamlit_callback: Optional[Callable[[Any], Any]] = None,
            session_state: SessionState = None,
    ):
        self.name = name
        self.parent = parent
        self.base_state_key = base_state_key
        self.replicated_state_keys: List[str] = replicated_state_keys or []
        self.lazy_state_keys: List[str] = lazy_state_keys or []

        if widget_callback is not None:
            self.widget = widget_callback

        if to_streamlit_callback is not None:
            self.to_streamlit = to_streamlit_callback

        if from_streamlit_callback is not None:
            self.from_streamlit = from_streamlit_callback

        if session_state is None:
            session_state = st.session_state
        self.session_state: SessionState = session_state

        # self.enabled = enabled
        # if self.enabled_key not in self.session_state:
        #     self.session_state[self.enabled_key] = enabled

        self.set_initial_value(value)

        self._value = value
        if self.base_state_key not in self.session_state:
            self.session_state[self.base_state_key] = self.to_streamlit(value)

    def widget(self, **kwargs) -> Any:
        raise NotImplementedError

    def from_streamlit(self, v: Any) -> T:
        return v

    def to_streamlit(self, v: T) -> Any:
        return v

    def set_initial_value(self, value: T):
        """
        The initial value uses st.session_state.
        This is required in the case of an Optional[BaseModel].
        We still want to persist downstream fields in that situation.
        If we don't, things get weird.
        """
        initial_state_key = f"{self.base_state_key}._initial_value"
        if initial_state_key not in self.session_state:
            self._initial_value = self.session_state[initial_state_key] = value
        else:
            self._initial_value = self.session_state[initial_state_key]

    # @property
    # def enabled_key(self) -> str:
    #     return f"{self.base_state_key}._enabled"
    #
    # @property
    # def enabled(self) -> bool:
    #     return self._enabled
    #
    # @enabled.setter
    # def enabled(self, v: bool) -> None:
    #     self._enabled = self.session_state[self.enabled_key] = v

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
            candidate_key = f"{self.base_state_key}._state_ref.{i}"
            if candidate_key not in key_list:
                return candidate_key
        else:
            raise ValueError(
                "Really? Over 100k keys??"
                " -- Either that, or a rare and unusual error has occurred."
                " Please file a bug report if you see this"
                " and are also sure you aren't doing anything too crazy."
            )

    def sync(self, update_lazy: bool = True):
        validated_value = self.to_streamlit(self.value)

        log.debug(f"Syncing {self} with value {validated_value} and update_lazy={update_lazy}")

        # TODO:
        #  Do we actually need to update self.replicated_state_keys????
        #  Causes issues with DateRange type to do so.
        #  I see no evidence so far that not updating replicated states leads to unintended consequences
        # for key in [self.base_state_key] + self.replicated_state_keys:
        #     self.session_state[key] = validated_value
        self.session_state[self.base_state_key] = validated_value
        if update_lazy:
            for key in self.lazy_state_keys:
                self.session_state[key] = validated_value

    def gen_key(self, key_suffix: Optional[str] = None) -> str:
        """Stateless operation"""
        if not key_suffix:
            return self.next_key()
        else:
            return f"{self.base_state_key}.{key_suffix}"
