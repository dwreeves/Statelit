# Changelog

### `0.1.1`

- Fixed minor bug in `dict[any, bool]` implementation

### `0.1.0`

- Add multiselect support for both `dict[any, bool]` and `set[enum.Enum]` types.
- Made `find_implementation()` more sophisticated, allowing it to resolve more complex types.

### `0.0.5`

- Added support for `tuple[int, int]`, `tuple[float, float]`, `tuple[decimal.Decimal, decimal.Decimal]`, and `tuple[datetime.date, datetime.date]`. Note: These do not work with lazy state.

Misc. notes:

- It's clear that the lazy state either needs a huge overhaul, or I should be calling `st.warning()` when incompatible types are used.

### `0.0.4`

- Added support for `Optional[T]` types + a hook for disabling fields.
- Added support for `Decimal` type.

Misc. notes:

- API works well, save for known bugs with `"lazy"` states, but the internals are getting a bit wonky and WET. Strongly considering refactoring at some point.

### `0.0.3`

- Added support for `list`, `dict`, and `statelit.types.DateRange` types.

### `0.0.2`

- Misc. bugfixes

### `0.0.1`

- First release
