from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

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
        (dict, "dict type"),
        (Dict[str, str], "dict type"),
        (list, "list type"),
        (List[int], "list type"),
        (Optional[int], "integer type"),
        (Optional[A], "A type"),
        (Optional[SomeIntEnum], "enum type"),
        (Optional[Dict[str, str]], "dict type"),
        (Optional[List[int]], "list type"),
        (Tuple[List[float], Dict[str, int]], "tuple[list[float], dict[str, int]] type"),
        (Tuple[List[float], Dict[int, int]], "tuple[list[float], dict] type"),
        (Tuple[List[float], Dict[StringSubtype, int]], "tuple[list[float], dict[str, int]] type"),
        (Tuple[List[float], Dict[StringSubtype, SomeIntEnum]], "tuple[list[float], dict[str, int]] type"),
        (Tuple[List[float], Dict[str, float]], "tuple[list[float], dict] type"),
        (Tuple[List[int], dict], "tuple type"),
        (Tuple[str, int], "tuple[str, int] type"),
        (Dict[str, bool], "dict[any, int] type"),
        (Dict[str, int], "dict[any, int] type"),
        pytest.param(
            Dict[str, SomeIntEnum], "dict[any, SomeIntEnum] type",
            marks=pytest.mark.xfail(reason="MRO not supported")
        ),
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
        B: "B type",
        dict: "dict type",
        list: "list type",
        tuple: "tuple type",
        Tuple[str, int]: "tuple[str, int] type",
        Tuple[List[float], dict]: "tuple[list[float], dict] type",
        Tuple[List[float], Dict[str, int]]: "tuple[list[float], dict[str, int]] type",
        Dict[Any, int]: "dict[any, int] type",
        Dict[Any, SomeIntEnum]: "dict[any, SomeIntEnum] type",
    }

    output = find_implementation(input, registry=registry)
    assert output == expected_output
