import streamlit as st
from pydantic import BaseModel

from statelit import StateManager


class SimpleExample(BaseModel):
    a: float = 10.0
    b: float = 10.0
    msg: str = "Hello, world!"


state_manager_simple = StateManager(SimpleExample)


if st.session_state.get("json_indent_size") is not None:
    state_manager_simple.statelit_model.json_indent_size = st.session_state["json_indent_size"]
    state_manager_simple.sync()


st.title("Statelit Demo - Basic Concepts")
st.markdown("This demo shows basic concepts about how dashboards are managed by Statelit.")
st.header("Why Statelit?")

st.markdown("""\
- 💻 **Simpler code:** Just define a Pydantic model, and you get all your widgets for free.
- 💾 **Save your work:** Save interesting things you see in an exploratory dashboard that you can come back to later.
- 🔗 **Sharing:** Share interesting insights with your colleagues by giving them a JSON.
- 👩‍🔧 **Pydantic is useful:** If you build an API that uses Pydantic, interoperating your schema with a dashboard is
   a great way to explore how your app works, especially for machine learning and other quantitative applications.
   Statelit makes this much easier.
""")

st.markdown("---")
st.header("Part 1 - State representations")
st.markdown(
    "State is represented and validated using Pydantic."
    "\n\n"
    "The class definition of a `BaseModel` determines data types and all fields managed by Statelit."
    " This `Type[BaseModel]` is passed into `state_manager = Statelit(some_model_type_here)`."
    " The resulting object controls the management of the state of a Pydantic model object,"
    " located at `state_manager.pydantic_obj`."
    "\n\n"
    "It sounds very abstract, but it's quite simple in action:"
)

st.code("""\
import streamlit as st
from pydantic import BaseModel
from statelit import StateManager

class SimpleExample(BaseModel):
    a: float = 10.0
    b: float = 10.0
    msg: str = "Hello, world!"

state_manager = StateManager(SimpleExample)
""", language="python")

st.markdown(
    "There are two main ways to interact with the state:"
    "\n- via widgets for each field"
    "\n- via a JSON that controls the whole model"
    "\n"
    "Most changes to a widget will automatically update all other associated states,"
    " with the exception of `'lazy'` states, which pull new updates but do not push out updates."
    "\n\n"
    "Play around below to get a feel for how it works:"
)

st.markdown("")

col1, col2 = st.columns(2)

with col1:
    st.code(">>> state = state_manager.form()", language="python")
    state = state_manager_simple.form()

with col2:

    if st.session_state.get("show_text_area_state_as") == "Replicated":
        st.code(">>> state_manager.text_area()")
        s = state_manager_simple.text_area(
            help="I will try my best to stay in sync with the object state.",
            key_suffix="replicated_text",
            height=150
        )
    else:
        st.code(">>> state_manager.lazy_text_area()")
        state_manager_simple.lazy_text_area(
            help="I won't modify the object state unless you click 'Apply'.",
            key_suffix="lazy_text",
            height=150
        )

with st.expander("JSON Options"):
    st.radio(
        "State Type",
        options=["Lazy", "Replicated"],
        key="show_text_area_state_as",
    )
    st.slider(label="Indent Size", min_value=0, max_value=8, step=2, value=2, key="json_indent_size",
              help="Default is 2")
    st.code(f">>> state_manager.statelit_model.json_indent_size = {st.session_state['json_indent_size']}")

st.markdown("")

st.markdown("The widgets will stay synced with the Pydantic model object as you make changes above:")

st.code(f"""\
>>> print(state)
{state!r}

>>> print(type(state))
{type(state)!r}

>>> print(state.a * state.b)
{state.a * state.b}

>>> print(state.msg)
{state.msg}

""", language="python")

st.markdown("---")
st.header("Part 2 - Data types")

st.markdown("""\
Statelit supports a lot of data types, and more supported data types are being added as Statelit grows.
Check the documentation for a list of all data types.

The purpose of this section is to go a little crazy and show you everything Statelit can do.

**Note that the majority of the code is just defining the types, and `Statelit` takes up just a couple lines.**
Statelit makes writing interactive dashboards much easier.
""")

with st.expander("Code", expanded=False):
    st.code(r"""from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

import streamlit as st
from pydantic import BaseModel
from pydantic import Field
from pydantic import conint
from pydantic.color import Color

from statelit import StateManager

class SmallModel(BaseModel):
    a: int = 100

PositiveInt = conint(gt=0)

class ExampleEnum(int, Enum):
    FOO = 1
    BAR = 2
    BAZ = 3

class BigExample(BaseModel):

    class Config:
        streamlit_label_generator = lambda x: x.replace("_", " ").title()  # noqa: #731

    flag: bool = True

    example_enum_field: ExampleEnum = 2

    # You can also use the statelit.types.DateRange type directly.
    date_range_field: Tuple[date, date] = ["2022-03-14", "2022-07-04"]

    json_data: Dict[str, List[int]] = {"some_key": [4, 5, 6]}

    constrained_int: int = Field(default=3, ge=0, le=10, description="Must be 0 to 10.")

    optional_positive_int_range: Optional[Tuple[PositiveInt, PositiveInt]] = (1, 100)

    # There are *two* ways to do multiselects: Dict[Any, bool] and Set[Enum].

    multiselect_dict: Dict[str, bool] = {"a": False, "b": True, "c": False, "d": False}

    multiselect_enum: Set[ExampleEnum] = {ExampleEnum.FOO}

    very_precise_decimal: Decimal = Decimal("1.23456")

    undefined_int: Optional[int] = Field(
        default=None,
        description="It is _not_ recommended that you leave default values undefined,"
                    " e.g. `some_field: Optional[int] = None`, or simply `some_field: Optional[int]`."
                    " That said, Statelit will still try to assign a reasonable default value"
                    " if the default is `None`."
    )

    large_optional_text: str = "Including a new line in the default\ncauses a `text_area` to appear"

    very_large_text: Optional[str] = Field(
        title="Very Large Text Area",
        default="Statelit hooks into a lot of Pydantic internals."
                "\nCheck out all the neat things you can do with Statelit!",
        streamlit_widget=lambda **kwargs: st.text_area(height=200, **kwargs),
        streamlit_disabled=True,
        description="Find this description of the Pydantic field in the 'help' text for this widget!"
    )

    some_date: date = date(2015, 3, 14)

    some_color: Color = "olive"

    some_pydantic_model: Optional[SmallModel] = SmallModel()

big_state_manager = StateManager(BigExample)

st.text("Let's generate a big form! 🙂")
big_state = big_state_manager.form()""")

with st.expander("Form"):
    from datetime import date
    from decimal import Decimal
    from enum import Enum
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Set
    from typing import Tuple

    import streamlit as st
    from pydantic import BaseModel
    from pydantic import Field
    from pydantic import conint
    from pydantic.color import Color

    from statelit import StateManager

    class SmallModel(BaseModel):
        a: int = 100

    PositiveInt = conint(gt=0)

    class ExampleEnum(int, Enum):
        FOO = 1
        BAR = 2
        BAZ = 3

    class BigExample(BaseModel):

        class Config:
            streamlit_label_generator = lambda x: x.replace("_", " ").title()  # noqa: #731

        flag: bool = True

        example_enum_field: ExampleEnum = 2

        # You can also use the statelit.types.DateRange type directly.
        date_range_field: Tuple[date, date] = ["2022-03-14", "2022-07-04"]

        json_data: Dict[str, List[int]] = {"some_key": [4, 5, 6]}

        constrained_int: int = Field(default=3, ge=0, le=10, description="Must be 0 to 10.")

        optional_positive_int_range: Optional[Tuple[PositiveInt, PositiveInt]] = (1, 100)

        # There are *two* ways to do multiselects: Dict[Any, bool] and Set[Enum].

        multiselect_dict: Dict[str, bool] = {"a": False, "b": True, "c": False, "d": False}

        multiselect_enum: Set[ExampleEnum] = {ExampleEnum.FOO}

        very_precise_decimal: Decimal = Decimal("1.23456")

        undefined_int: Optional[int] = Field(
            default=None,
            description="It is _not_ recommended that you leave default values undefined,"
                        " e.g. `some_field: Optional[int] = None`, or simply `some_field: Optional[int]`."
                        " That said, Statelit will still try to assign a reasonable default value"
                        " if the default is `None`."
        )

        large_optional_text: str = "Including a new line in the default\ncauses a `text_area` to appear"

        very_large_text: Optional[str] = Field(
            title="Very Large Text Area",
            default="Statelit hooks into a lot of Pydantic internals."
                    "\nCheck out all the neat things you can do with Statelit!",
            streamlit_widget=lambda **kwargs: st.text_area(height=200, **kwargs),
            streamlit_disabled=True,
            description="Find this description of the Pydantic field in the 'help' text for this widget!"
        )

        some_date: date = date(2015, 3, 14)

        some_color: Color = "olive"

        some_pydantic_model: Optional[SmallModel] = SmallModel()

    big_state_manager = StateManager(BigExample)

    st.text("Let's generate a big form! 🙂")
    big_state = big_state_manager.form()

with st.expander("State (pretty)"):
    st.markdown("The `.code()` method calls `st.code()` and represents the JSON with syntax highlighting.")
    big_state_manager.code()


with st.expander("State (lazy text area)"):
    st.markdown("`DateRange` type and `Optional[T]` do not currently work with `lazy_text_area()`."
                " Sorry about that.")
    big_state_manager.lazy_text_area(height=300)


with st.expander("State (eager text area)"):
    big_state_manager.text_area(height=300)
