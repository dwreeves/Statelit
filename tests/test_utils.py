from enum import Enum

import pytest

from statelit.utils.misc import chain_two_callables
from statelit.utils.misc import get_next_availble_key
from statelit.utils.mro import find_implementation


class SomeIntEnum(int, Enum):
    FOO = 1
    BAR = 2


class StringSubtype(str):
    pass


class A:
    pass


class B:
    pass


class C(A, B):
    pass


def test_chain_two_callables():
    f_was_called = False

    def f():
        nonlocal f_was_called
        f_was_called = True

    def g(a: int):
        return a * 2

    f_g = chain_two_callables(f, g)

    assert not f_was_called

    res = f_g(5)

    assert res == 10
    assert f_was_called


def test_get_next_availble_key():
    data = {
        "foo.0": None,
        "foo.1": None,
    }
    res = get_next_availble_key("foo", data)
    assert res == "foo.2"


def test_get_next_availble_key_hit_limit():
    data = {f"foo.{i}" for i in range(100)}
    with pytest.raises(ValueError):
        get_next_availble_key("foo", data, max_keys=50)


@pytest.mark.parametrize(
    ["input", "expected_output"],
    [
        (int, "integer type"),
        (SomeIntEnum, "enum type"),
        (str, "string type"),
        (StringSubtype, "string type"),
        (A, "A type"),
        (B, "B type"),
        (C, "A type"),
    ]
)
def test_find_implementation(input, expected_output):

    # Deliberately exclude `SomeIntEnum` --> should default to Enum, not int
    # Deliberately exclude `A` --> Should use MRO to determine A comes first.

    registry = {
        int: "integer type",
        str: "string type",
        Enum: "enum type",
        A: "A type",
        B: "B type"
    }

    output = find_implementation(input, registry=registry)
    assert output == expected_output
