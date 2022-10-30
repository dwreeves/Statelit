import json
from datetime import date
from datetime import datetime

import pytest
from pydantic.color import Color

from statelit.json import statelit_encoder


@pytest.mark.parametrize(
    ["input", "expected_output"],
    [
        (date(2001, 2, 3), '"2001-02-03"'),
        (datetime(2001, 2, 3, 4, 5, 6), '"2001-02-03T04:05:06"'),
        (Color((1, 12, 123)), '"#010c7b"'),
    ]
)
def test_encoding(input, expected_output):
    output = json.dumps(input, default=statelit_encoder)
    assert output == expected_output
