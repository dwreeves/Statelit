# Most code here is mostly pulled from functools.py
#
# The C3 linearization algorithm resolves situations where types are subclassed.
#
# Note however that C3 does not work the way we want for Enums. Enum subclasses
# will look like this:
#
# class Foo(str, Enum):
#     A = "A"
#
# And when deciding between an implementation of str and Enum, C3 linearization
# will pick str because Enum comes second in the hierarchy. So we do need to
# override this behavior and manually pick Enums. In the future, there may be
# a better option than this.
#
# Additionally, we want to make sure the typing module is supported, so some
# cleanup is done on the type.


from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import TypeVar
from typing import Union

from pydantic.utils import get_args
from pydantic.utils import get_origin
from pydantic.utils import lenient_issubclass


T = TypeVar("T")
Ty = TypeVar("Ty", bound=type)


def extract_type_from_optional(cls: List[Union[type, Tuple[type, Tuple[type, ...]]]]) -> type:
    """If cls == Optional[T], return T. Else return cls"""
    if get_origin(cls) is Union:
        new_types = list(filter(lambda _: _ is not type(None), get_args(cls)))  # noqa: E721
        if len(new_types) == 1:
            return new_types[0]
    return cls


def _c3_merge(sequences):
    """Merges MROs in *sequences* to a single MRO using the C3 algorithm.

    Adapted from http://www.python.org/download/releases/2.3/mro/.

    """
    result = []
    candidate = None
    while True:
        sequences = [s for s in sequences if s]   # purge empty sequences
        if not sequences:
            return result
        for s1 in sequences:   # find merge candidates among seq heads
            candidate = s1[0]
            for s2 in sequences:
                if candidate in s2[1:]:
                    candidate = None
                    break      # reject the current head, it appears later
            else:
                break
        if candidate is None:
            raise RuntimeError("Inconsistent hierarchy")
        result.append(candidate)
        # remove the chosen candidate
        for seq in sequences:
            if seq[0] == candidate:
                del seq[0]


def _c3_mro(cls, abcs=None):
    """Computes the method resolution order using extended C3 linearization.

    If no *abcs* are given, the algorithm works exactly like the built-in C3
    linearization used for method resolution.

    If given, *abcs* is a list of abstract base classes that should be inserted
    into the resulting MRO. Unrelated ABCs are ignored and don't end up in the
    result. The algorithm inserts ABCs where their functionality is introduced,
    i.e. issubclass(cls, abc) returns True for the class itself but returns
    False for all its direct base classes. Implicit ABCs for a given class
    (either registered or inferred from the presence of a special method like
    __len__) are inserted directly after the last ABC explicitly listed in the
    MRO of said class. If two implicit ABCs end up next to each other in the
    resulting MRO, their ordering depends on the order of types in *abcs*.

    """
    for i, base in enumerate(reversed(cls.__bases__)):
        if hasattr(base, '__abstractmethods__'):
            boundary = len(cls.__bases__) - i
            break   # Bases up to the last explicit ABC are considered first.
    else:
        boundary = 0
    abcs = list(abcs) if abcs else []
    explicit_bases = list(cls.__bases__[:boundary])
    abstract_bases = []
    other_bases = list(cls.__bases__[boundary:])
    for base in abcs:
        if (
            lenient_issubclass(cls, base)
            and not any(lenient_issubclass(b, base) for b in cls.__bases__)
        ):
            # If *cls* is the class that introduces behaviour described by
            # an ABC *base*, insert said ABC to its MRO.
            abstract_bases.append(base)
    for base in abstract_bases:
        abcs.remove(base)
    explicit_c3_mros = [_c3_mro(base, abcs=abcs) for base in explicit_bases]
    abstract_c3_mros = [_c3_mro(base, abcs=abcs) for base in abstract_bases]
    other_c3_mros = [_c3_mro(base, abcs=abcs) for base in other_bases]
    return _c3_merge(
        [[cls]] + explicit_c3_mros + abstract_c3_mros + other_c3_mros +  # noqa: W504
        [explicit_bases] + [abstract_bases] + [other_bases]
    )


def _compose_mro(cls, types):
    """Calculates the method resolution order for a given class *cls*.

    Includes relevant abstract base classes (with their respective bases) from
    the *types* iterable. Uses a modified C3 linearization algorithm.

    """
    bases = set(cls.__mro__)
    # Remove entries which are already present in the __mro__ or unrelated.

    def is_related(typ):
        return typ not in bases and hasattr(typ, '__mro__') and lenient_issubclass(cls, typ)

    types = [n for n in types if is_related(n)]
    # Remove entries which are strict bases of other entries (they will end up
    # in the MRO anyway.

    def is_strict_base(typ):
        for other in types:
            if typ != other and typ in other.__mro__:
                return True
        return False

    types = [n for n in types if not is_strict_base(n)]
    # Subclasses of the ABCs in *types* which are also implemented by
    # *cls* can be used to stabilize ABC ordering.
    type_set = set(types)
    mro = []
    for typ in types:
        found = []
        for sub in typ.__subclasses__():
            if sub not in bases and lenient_issubclass(cls, sub):
                found.append([s for s in sub.__mro__ if s in type_set])
        if not found:
            mro.append(typ)
            continue
        # Favor subclasses with the biggest number of useful bases
        found.sort(key=len, reverse=True)
        for sub in found:
            for subcls in sub:
                if subcls not in mro:
                    mro.append(subcls)
    return _c3_mro(cls, abcs=mro)


def _find_single_impl(cls: type, registry: Dict[type, T]) -> Optional[T]:
    """Returns the best matching implementation from *registry* for type *cls*.

    Where there is no registered implementation for a specific type, its method
    resolution order is used to find a more generic implementation.

    Note: if *registry* does not contain an implementation for the base
    *object* type, this function may return None.

    """
    mro = _compose_mro(cls, registry.keys())
    match = None
    for t in mro:
        if match is not None:
            # If *match* is an implicit ABC but there is another unrelated,
            # equally matching implicit ABC, refuse the temptation to guess.
            if (
                    t in registry and t not in cls.__mro__
                    and match not in cls.__mro__
                    and not lenient_issubclass(match, t)
            ):
                raise RuntimeError(f"Ambiguous dispatch: {match} or {t}")
            break
        if t in registry:
            match = t
    return registry.get(match)


def _find_all_impl(cls: Tuple[type, ...], registry: Dict[Tuple[type, ...], T]) -> Dict[Ty, T]:
    mro = _compose_mro(cls, registry.keys())
    matches = {}
    for t in mro:
        if t in registry:
            matches[t] = registry[t]
    return matches


def _lenient_issubclass_respect_origin_plus_depth(cls, supercls, depth: int = 1) -> Tuple[int, bool]:
    cls_origin = get_origin(cls)
    supercls_origin = get_origin(supercls)

    # treat `any` generically
    if cls_origin and get_args(cls) in [(Any, ), (any, )]:
        # treat any
        cls = cls_origin
        cls_origin = None
    if supercls_origin and get_args(supercls) in [(Any, ), (any, )]:
        # treat any
        supercls = supercls_origin
        supercls_origin = None

    if cls_origin and supercls_origin:
        if not lenient_issubclass(cls_origin, supercls_origin):
            return depth, False
        cls_args = get_args(cls)
        supercls_args = get_args(supercls)
        if not len(cls_args) == len(supercls_args):
            return depth, False
        _d = depth
        for ca, sa in zip(cls_args, supercls_args):
            _check_depth, check = _lenient_issubclass_respect_origin_plus_depth(ca, sa, depth=1)
            _d += _check_depth
            if not check:
                return depth, False
        else:
            return _d, True
    elif cls_origin is not None and supercls_origin is None:
        # e.g. cls_origin == List[str] and supercls_origin == list
        # in above example, cls_origin is superclass of supercls_origin
        return _lenient_issubclass_respect_origin_plus_depth(cls_origin, supercls, depth=depth)
    elif cls_origin is None and supercls_origin is not None:
        return depth, False
    elif supercls in (Any, any):
        return depth, True
    else:
        # default to lenient_issubclass implementation.
        return depth, lenient_issubclass(cls, supercls)


def lenient_issubclass_respect_origin(cls, supercls):
    return _lenient_issubclass_respect_origin_plus_depth(cls, supercls)[0]


def find_implementation_traversing_origins_and_args(cls: type, registry: Dict[type, T]) -> Optional[T]:
    # Motivting example:
    #
    # registry has:
    # - list[dict]
    # - list[dict[str, list]]
    # - list[dict, [str, list[str]]
    #
    # if cls is list[dict, [str, list[int]], we want to return implementation
    # for list[dict[str, list]].
    #
    # The solution is keep going deeper until we have exactly 1 impl.
    #
    # this approach is pretty inefficient, but it does work.
    #
    # care is taken to make sure that for simple lookups, inefficiency isn't a
    # big deal, since complex typing should be very rare edge case. This is
    # mainly here because, why not support complex types? :)
    filtered_registry_keys = []
    max_depth = -1
    for k in registry:
        depth, is_valid = _lenient_issubclass_respect_origin_plus_depth(cls, k)
        if is_valid:
            if depth > max_depth:
                filtered_registry_keys = [k]
                max_depth = depth
            elif depth == max_depth:
                filtered_registry_keys.append(k)
            else:
                pass
    if len(filtered_registry_keys) == 1:
        return filtered_registry_keys[0]
    elif len(filtered_registry_keys) == 0:
        return None
    else:
        raise RuntimeError(
            f"There were {len(filtered_registry_keys)} implementations found that were valid:"
            f" {filtered_registry_keys}."
            "\n\n"
            "In many cases, this error will be raised because MRO resolution is not supported"
            " for registered implementations of complex types."
            "\n\n"
            "For example, if G is subtype of T, and List[G] and List[T] are both in the registry,"
            " then List[G] will fail to resolve. (List[T] should work though.)"
            "\n\n"
            "If you want to support MRO resolution of complex types, help me out and contribute"
            " to this library! :)"
        )


def find_implementation(cls: type, registry: Dict[type, T]) -> Optional[T]:
    cls = extract_type_from_optional(cls)

    origin = get_origin(cls)
    if origin is not None:
        # In the case that origin is not None, we avoid using the MRO.
        k = find_implementation_traversing_origins_and_args(cls=cls, registry=registry)
        return registry.get(k)

    # Give priority to Enum implementations
    if lenient_issubclass(cls, Enum):
        _sub_registry = {k: v for k, v in registry.items() if lenient_issubclass(k, Enum)}
        maybe_find_implementation = _find_single_impl(cls=cls, registry=_sub_registry)
        if maybe_find_implementation:
            return maybe_find_implementation

    return _find_single_impl(cls=cls, registry=registry)
