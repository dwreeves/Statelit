from functools import wraps
from typing import Sequence


def get_next_availble_key(
        prefix: str,
        data: Sequence[str],
        max_keys: int = 100_000
) -> str:
    for i in range(max_keys):
        potential_key = ".".join([prefix, str(i)])
        if potential_key not in data:
            return potential_key
    else:
        raise ValueError(
            "Something weird happened."
            " There was not a valid place to assign this key between"
            f" {prefix}.0 to {prefix}.{max_keys}"
        )


def chain_two_callables(func1: callable, func2: callable):
    """This is used when users pass their own custom callbacks to Streamlit widgets."""
    @wraps(func2)
    def _wraps(*args, **kwargs):
        func1()
        return func2(*args, **kwargs)
    return _wraps
