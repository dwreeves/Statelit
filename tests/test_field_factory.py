from datetime import date
from datetime import datetime
from datetime import time
from enum import Enum
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import BaseModel
from pydantic import Field
from pydantic import create_model
from pydantic.color import Color

import statelit.field_factory.main
from statelit.field_factory.main import DefaultFieldFactory
from statelit.state.base import StatefulObjectBase


class SubModel(BaseModel):
    x: int = 3


class BasicEnum(int, Enum):
    A = 1
    B = 2


@pytest.fixture
def field_factory(session_state):
    obj = DefaultFieldFactory("test_prefix", session_state)
    return obj


@pytest.mark.parametrize(
    ("field_definition", "calls"),
    [
        ((str, "lorem ipsum"), "text_input"),
        ((str, "lorem\nipsum"), "text_area"),
        ((int, 123), "number_input"),
        ((int, Field(default=123, ge=0)), "number_input"),
        ((int, Field(default=123, ge=0, le=1000)), "slider"),
        ((float, 123.4), "number_input"),
        ((float, Field(default=123.4, ge=0.0)), "number_input"),
        ((float, Field(default=123.4, ge=0.0, le=1000.0)), "slider"),
        ((bool, True), "checkbox"),
        ((BasicEnum, BasicEnum.A), "selectbox"),
        ((time, time(3, 14, 15)), "time_input"),
        ((date, date(1970, 3, 14)), "date_input"),
        ((datetime, datetime(1970, 3, 14, 15, 9, 26)), "date_input"),
        ((Color, "red"), "color_picker"),
        ((SubModel, SubModel()), "text_area"),
    ]
)
def test_default_field_factory(field_definition, calls, field_factory):
    model = create_model("FooModel", bar=field_definition)
    pydantic_obj = model()

    with patch.object(statelit.field_factory.main.st, calls) as mocked_func:

        statelit_obj: StatefulObjectBase = field_factory(
            value=pydantic_obj.bar,
            field=pydantic_obj.__fields__["bar"],
            model=type(pydantic_obj)
        )

        statelit_obj.widget()

    assert isinstance(statelit_obj, StatefulObjectBase)
    mocked_func.assert_called_once()
