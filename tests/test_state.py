import pytest

from statelit.state.base import StatefulObjectBase


@pytest.fixture
def integer_10_obj(session_state):
    obj = StatefulObjectBase(
        value=10,
        base_state_key="test_case_example_key",
        session_state=session_state
    )

    yield obj


def test_base_key_value(integer_10_obj: StatefulObjectBase, session_state):
    session_state[integer_10_obj.base_state_key] = 10
    assert session_state[integer_10_obj.base_state_key] == 10
