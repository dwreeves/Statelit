import json
from datetime import date
from datetime import datetime

import pandas as pd
import pytest
from pydantic.color import Color

from statelit.json import statelit_encoder
from statelit.types import DateRange


@pytest.mark.parametrize(
    ["input", "expected_output"],
    [
        (date(2001, 2, 3), '"2001-02-03"'),
        (datetime(2001, 2, 3, 4, 5, 6), '"2001-02-03T04:05:06"'),
        (Color((1, 12, 123)), '"#010c7b"'),
        (
            DateRange(lower=date(2022, 1, 1), upper=None),
            '["2022-01-01", null]'
        ),
        (
            DateRange(lower=date(2022, 1, 1), upper=date(2023, 3, 14)),
            '["2022-01-01", "2023-03-14"]'
        ),
        (
            pd.DataFrame([{"x": 1, "y": "foo"}, {"x": 2, "y": "bar"}]),
            '[{"x": 1, "y": "foo"}, {"x": 2, "y": "bar"}]'
        )
    ]
)
def test_encoding(input, expected_output):
    output = json.dumps(input, default=statelit_encoder)
    assert output == expected_output
