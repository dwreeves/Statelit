from typing import Any

from pydantic.json import pydantic_encoder


# from statelit.types import DateRange


__all__ = ["statelit_encoder"]


def statelit_encoder(o: Any) -> Any:
    # if isinstance(o, DateRange):
    #     return [o.lower, o.upper]
    # else:
    #     return pydantic_encoder(o)
    return pydantic_encoder(o)
