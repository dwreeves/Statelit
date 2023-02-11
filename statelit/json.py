from typing import Any

from pydantic.json import pydantic_encoder

from statelit.types import DateRange


__all__ = ["statelit_encoder"]


def _is_dataframe(o: Any):
    # NOTE: Not currently being used
    try:
        import pandas
    except (ImportError, AttributeError) as e:
        return False
    else:
        return hasattr(pandas, "DataFrame") and isinstance(o, pandas.DataFrame)


def statelit_encoder(o: Any) -> Any:
    if isinstance(o, DateRange):
        return [o.lower, o.upper]
    elif _is_dataframe(o):
        return o.to_dict(orient="records")
    else:
        return pydantic_encoder(o)
