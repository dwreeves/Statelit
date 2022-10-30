# UNDER CONSTRUCTION! CHECK BACK SOON! :)

# from typing import NamedTuple, Any, Dict, Iterable, Optional
# from datetime import date
# from pydantic.fields import ModelField
# from pydantic import BaseConfig
# from pydantic.datetime_parse import parse_date
#
#
# class DateRange(NamedTuple):
#     lower: date
#     upper: Optional[date]
#
#     @classmethod
#     def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
#         pass
#
#     @classmethod
#     def __get_validators__(cls):
#         yield cls.validate
#
#     @classmethod
#     def validate(cls, value: Any, field: ModelField, config: BaseConfig):
#         if value.__class__ == cls:
#             return value
#         if isinstance(value, dict):
#             return cls(lower=value["lower"], upper=value["upper"])
#         if isinstance(value, Iterable):
#             i = iter(value)
#             lower = next(i)
#             try:
#                 upper = next(i)
#             except StopIteration:
#                 upper = None
#             return cls(lower=parse_date(lower), upper=parse_date(upper))
#         else:
#             raise ValueError('idk lol')
