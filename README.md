<p align="center">
    <img src="https://github.com/dwreeves/statelit/workflows/tests/badge.svg" alt="Tests badge">
    <img src="https://github.com/dwreeves/statelit/workflows/docs/badge.svg" alt="Docs badge">
</p>
<p align="center">
    <img src="https://raw.githubusercontent.com/dwreeves/statelit/main/docs/src/img/statelit-banner.png" alt="Statelit logo">
</p>
<p align="center">
    <em>Easy state management in Streamlit with Pydantic.</em>
</p>

---

<p align="center">
    <a href="https://dwreeves-statelit-demo-streamlit-app-e9b0nf.streamlitapp.com/"><b>✨ Statelit demo here! ✨</b></a>
</p>

---

# Overview

**Statelit** is an easy way to manage the state of your Streamlit applications using Pydantic.
**Statelit** allows you to import and export dashboard states with just a few extra lines of code.

Reasons to use **Statelit**:

- 💻 **Simpler code:** Just define a Pydantic model, and you get all your widgets for free.
- 💾 **Save your work:** Save interesting things you see in an exploratory dashboard that you can come back to later.
- 🔗 **Sharing:** Share interesting insights with your colleagues by giving them a JSON.
- 👩‍🔧 **Pydantic is useful:** If you build an API that uses Pydantic, interoperating your schema with a dashboard is
   a great way to explore how your app works, especially for machine learning and other quantitative applications.
   Statelit makes this much easier.

_(Note: Statelit is still under development.
The current verison is `0.0.2`;
the first stable release will be version `0.1.0`.)_

# Install

Via pip:

```shell
pip install statelit
```

# Example

<p align="center">
    <a href="https://dwreeves-statelit-demo-2-streamlit-app-fkrqyq.streamlitapp.com/"><b>✨ See the below example in action here! ✨</b></a>
</p>

```python
# Requires `pip install matplotlib numpy`
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from pydantic import BaseModel

from statelit import StateManager


class AppState(BaseModel):
    seed: int = 372193
    size: int = 10_000
    mu: float = 5.0
    sigma: float = 5.0
    log: bool = False


state_manager = StateManager(AppState)

with st.sidebar:
    state = state_manager.form()

with st.expander("State"):
    state_manager.text_area()

np.random.seed(state.seed)

arr = np.random.normal(state.mu, state.sigma, size=state.size)

if state.log:
    arr = np.log(arr)

fig, ax = plt.subplots()
ax.hist(arr, bins=20)

st.pyplot(fig)
```

See `example.py` for a more complicated example and a demo of all of **Statelit**'s features.

# API

## `StatelitModel` Attributes and Methods

The following attributes and methods are part of the public API and are considered stable.

### `StatelitModel().pydantic_obj`

Pydantic object being used by the `StatelitModel()`.

### `StatelitModel().widget()`

Render a single widget for a single field.

**Parameters:**

* `field_name: str` **(required)** - String name of the field to render a widget for.
* `key_suffix: Optional[str] = None` - Suffix to apply to the state key.
* `validate_output: bool = True` - If true, run the "`from_streamlit` callback" for this field before returning a value.
* `**kwargs` - Additional keyword arguments that will be passed to the Streamlit callback.

**Returns:** (`Any`) The value output by the Streamlit callback (i.e. the value of the widget), after running the `from_streamlit` callback if `validate_output` is True.

### `StatelitModel().form()`

Renders _all_ widgets for the entire Pydantic `BaseModel`. Widgets are rendered in the order they're defined in the model.

**Parameters:**

* `key_suffix: Optional[str] = None` - Suffix to apply to the state key.
* `exclude: Optional[List[str]] = None` - Which field names to exclude from rendering.
* `**kwargs` - Additional keyword arguments that will be passed to the Streamlit callback.

**Returns:** (`pydantic.BaseModel`) The Pydantic model object, `pydantic_obj`.

### `StatelitModel().code()`

Renders Markdown syntax highlighted version of the JSON state.

**Returns:** (`str`) JSON representation of the state.

### `StatelitModel().text_area()`

Renders the JSON state as a text field. The JSON can be modified, and changing its value will update all other fields to match.

**Parameters:**

* `key_suffix: Optional[str] = None` - Suffix to apply to the state key.
* `exclude: Optional[List[str]] = None` - Which field names to exclude from rendering.
* `validate_output: bool = True` - If true, run the "`from_streamlit` callback" before returning a value. In this case, validating the output is equivalent to converting the JSON `str` into the Pydantic object.
* `**kwargs` - Additional keyword arguments that will be passed to the Streamlit callback.

**Returns:** (`pydantic.BaseModel | str`) Either outputs the Pydantic object (equivalent to `StatelitModel().pydantic_obj`) if `validate_output` is `True`, or alternatively returns a `str` JSON representation of the state if `validate_output` is `False`.

### `StatelitModel().lazy_text_area()`

Renders the JSON state as a "lazy" text field. The JSON can be modified, but changes won't be saved until the "Apply" button is pressed.

**Parameters:**

* `key_suffix: Optional[str] = None` - Suffix to apply to the state key.
* `exclude: Optional[List[str]] = None` - Which field names to exclude from rendering.
* `validate_output: bool = True` - If true, run the "`from_streamlit` callback" before returning a value. In this case, validating the output is equivalent to converting the JSON `str` into the Pydantic object.
* `**kwargs` - Additional keyword arguments that will be passed to the Streamlit callback.

**Returns:** (`pydantic.BaseModel | str`) Either outputs the Pydantic object (equivalent to `StatelitModel().pydantic_obj`) if `validate_output` is `True`, or alternatively returns a `str` JSON representation of the state if `validate_output` is `False`.

## Types

The following implementations are considered stable:

|Type|Widget|Notes|
|---|---|---|
|`float`|`st.number_input`||
|`int`|`st.number_input`||
|`str`|`st.text_input` or `st.text_area`|`st.text_area` is used if the default value contains a `\n`; otherwise, `st.text_input` is used.|
|`enum.Enum`|`st.selectbox`|`st.radio` is also a good choice; set the `streamlit_widget` kwarg in the `Field()` to use that.|
|`datetime.date`|`st.date_input`||
|`datetime.time`|`st.time_input`||
|`pydantic.ConstrainedInt`|`st.slider`|Used when both `ge`/`gt` and `le`/`lt` are set; otherwise, use `st.number_input`|
|`pydantic.ConstrainedFloat`|`st.slider`|Used when both `ge`/`gt` and `le`/`lt` are set; otherwise, use `st.number_input`|
|`pydantic.color.Color`|`st.color_picker`|Colors are always converted to hex values.|

The following implementations are considered **experimental** and are potentially subject to some future changes:

|Type|Widget|Notes|
|---|---|---|
|`datetime.datetime`|`st.date_input`|Time component is always cast to `00:00:00`. For true datetimes, at the moment, it is suggested you use separate `datetime.date` and `datetime.time`s and manually combine them.|

## Notes on internals

Most users do not need this.

Note that Streamlit is a new project, and some of these implementations may be considered unstable until the `0.1.0` release.

### StatefulObjectBase

The `StatefulObjectBase` class is a Generic class that consists of shared internals for both model and field instances.

There are three types of state: `base`, `replicated`, and `lazy`:

* `base` state is the source of truth for all state. Each `StatefulObjectBase` has only one `base` state.
* `replicated` state is always kept in sync with base state. If `replicated` state changes, then `base` state is updated.
* `lazy` state is updated when `base` state updates, but changes to lazy state will not update the base state by itself (for example, updating a lazy-state text field does not update base state, but a button may trigger a callable that updates the base state from the lazy state).

State is represented by keys associated with each object. Note that keys are by default assigned automatically. If you want to support more dynamic rendering (that makes when widgets are rendered non-deterministic), please set a `key_suffix=`.

`StatefulObjectBase`s also have methods that allow for conversion between Statelit and Pydantic called `to_streamlit` and `from_streamlit`.

### FieldFactoryBase, DynamicFieldFactoryBase & DefaultFieldFactory

Converting a Pydantic model field to a Statelit field mostly consists of checking `pydantic.fields.ModelField.type_`. However, there are additional complications that allow for greater control.

### Converters vs Callbacks vs FieldFactories

A callback is a callable that comes in one of three types: it is either a `widget`, `to_streamlit`, or `from_streamlit`

A converter is a callable that takes in `(value: Any, field: pydantic.fields.ModelField, model: pydantic.BaseModel)`, and returns a callback.

A `FieldFactory` is a callable that takes in `(value: Any, field: pydantic.fields.ModelField, model: pydantic.BaseModel)`, and returns a `StatefulObjectBase`

# Trademark & Copyright

Streamlit is a trademark of Streamlit Inc.

This package is **unaffiliated** with Streamlit Inc. and Pydantic.
