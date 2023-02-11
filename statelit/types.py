# UNDER CONSTRUCTION! CHECK BACK SOON! :)

from datetime import date
from typing import Any
from typing import Dict
from typing import Iterable
from typing import NamedTuple
from typing import Optional

from pydantic import BaseConfig
from pydantic.datetime_parse import parse_date
from pydantic.fields import ModelField


def parse_date_allow_null(x):
    if x is None:
        return None
    else:
        return parse_date(x)


class DateRange(NamedTuple):
    lower: date
    upper: Optional[date]

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        pass

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: Any, field: ModelField, config: BaseConfig):
        if value.__class__ == cls:
            return value

        # Parse lower and upper separately
        if isinstance(value, date):
            lower = value
            upper = None
        elif isinstance(value, dict):
            lower = value["lower"]
            upper = value["upper"]
        elif isinstance(value, Iterable):
            i = iter(value)
            lower = next(i)
            try:
                upper = next(i)
            except StopIteration:
                upper = None
        else:
            raise ValueError("idk lol")

        if upper is not None and lower > upper:
            raise ValueError("Lower bound of range must be greater than upper bound of range")

        return cls(
            lower=parse_date(lower),
            upper=parse_date_allow_null(upper)
        )

    @classmethod
    def convert_to_streamlit(cls, v: Any, field: ModelField, config: BaseConfig, upper_is_optional: bool = True):
        if not isinstance(v, cls):
            v = cls.validate(v, field, config)
        v: cls
        if not upper_is_optional and v.upper is None:
            return v.lower, v.lower
        else:
            return v.lower, v.upper
