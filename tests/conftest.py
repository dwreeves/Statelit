import pytest
import streamlit as st
from streamlit.runtime.state.session_state import SessionState


@pytest.fixture(autouse=True)
def session_state(monkeypatch):
    data = SessionState()
    monkeypatch.setattr(st, "session_state", data)
    yield data
