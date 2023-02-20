from datetime import date
from datetime import datetime
from datetime import time
from decimal import Decimal
from enum import Enum
from typing import Dict
from typing import Optional
from typing import Set
from typing import Tuple
from unittest.mock import patch

import pytest
from pydantic import BaseModel
from pydantic import Field
from pydantic import PositiveInt
from pydantic import create_model
from pydantic.color import Color

import statelit.field_factory.main
from statelit.field_factory.main import DefaultFieldFactory
from statelit.state.base import StatefulObjectBase
from statelit.types import DateRange


class SubModel(BaseModel):
    x: int = 3


class BasicEnum(int, Enum):
    A = 1
    B = 2


@pytest.fixture
def field_factory(session_state):
    obj = DefaultFieldFactory("test_prefix", session_state)
    return obj


field_definitions_and_expected_calls = [
    ((str, "lorem ipsum"), "text_input"),
    ((int, 123), "number_input"),
    ((PositiveInt, 123), "number_input"),
    ((int, Field(default=123, ge=0)), "number_input"),
    ((Decimal, Decimal("0.123")), "number_input"),
    ((float, 123.4), "number_input"),
    ((float, Field(default=123.4, ge=0.0)), "number_input"),
    ((Tuple[float, float], [0.1, 0.99]), "slider"),
    ((Tuple[PositiveInt, PositiveInt], [1, 99]), "slider"),
    ((Tuple[Decimal, Decimal], [Decimal("1"), Decimal("99")]), "slider"),
    ((bool, True), "checkbox"),
    ((list, ["a", "b"]), "text_area"),
    ((set, {"a", "b"}), "text_area"),
    ((dict, {"foo": "bar"}), "text_area"),
    ((BasicEnum, BasicEnum.A), "selectbox"),
    ((time, time(3, 14, 15)), "time_input"),
    ((date, date(1970, 3, 14)), "date_input"),
    ((datetime, datetime(1970, 3, 14, 15, 9, 26)), "date_input"),
    ((Color, "red"), "color_picker"),
    ((SubModel, SubModel()), "text_area"),
    ((DateRange, ["2022-01-01", "2022-03-14"]), "date_input"),
    ((Tuple[date, date], ["2022-01-01", "2022-03-14"]), "date_input"),
    ((Set[BasicEnum], ["A"]), "multiselect"),
    ((Dict[str, int], {"abc": 123}), "text_area"),
    ((Dict[str, bool], {"abc": False}), "multiselect"),
]


@pytest.mark.parametrize(
    ("field_definition", "calls"),
    [
        *field_definitions_and_expected_calls,

        # The following don't apply to Optional[...] tests,
        # so just define them separately:

        ((str, "lorem\nipsum"), "text_area"),
        ((int, Field(default=123, ge=0, le=1000)), "slider"),
        ((float, Field(default=123.4, ge=0.0, le=1000.0)), "slider")
    ]
)
def test_default_field_factory(field_definition, calls, field_factory, session_state):
    model = create_model("FooModel", bar=field_definition)
    pydantic_obj = model()

    with patch.object(statelit.field_factory.main.st, calls) as mocked_func:

        statelit_obj: StatefulObjectBase = field_factory(
            value=getattr(pydantic_obj, "bar"),
            field=pydantic_obj.__fields__["bar"],
            model=type(pydantic_obj)
        )

        field_factory.session_state["foo"] = statelit_obj.value

        statelit_obj.widget(key="foo")

    assert isinstance(statelit_obj, StatefulObjectBase)
    mocked_func.assert_called_once()


@pytest.mark.parametrize(
    ("field_definition", "calls"),
    field_definitions_and_expected_calls
)
def test_default_field_factory_default_fallbacks(field_definition, calls, field_factory):
    model = create_model("FooModel", bar=(Optional[field_definition[0]], None))
    pydantic_obj = model()

    with patch.object(statelit.field_factory.main.st, calls) as mocked_func:

        statelit_obj: StatefulObjectBase = field_factory(
            value=getattr(pydantic_obj, "bar"),
            field=pydantic_obj.__fields__["bar"],
            model=type(pydantic_obj)
        )

        statelit_obj.widget(key=statelit_obj.base_state_key, on_change=lambda: None)

    assert isinstance(statelit_obj, StatefulObjectBase)

    mocked_func.assert_called()
