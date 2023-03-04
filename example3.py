# NOTE: WORK IN PROGRESS

from datetime import date
from enum import Enum
# from typing import Dict
# from typing import Tuple
from typing import Optional
from typing import Set

import altair as alt
# import numpy as np
import pandas as pd
import streamlit as st
from pydantic import BaseModel
from pydantic import Field
from pydantic import validator

from statelit import StateManager
from statelit.types import DateRange


df = pd.read_csv("assets/stock_prices.csv")
df["date"] = pd.to_datetime(df["date"]).dt.date
print(df["date"].iloc[0], type(df["date"].iloc[0]))
# df["log_price"] = np.log(df["price"])


stocks_list = df["ticker"].unique()

Stock = Enum("Stock", {i: i for i in stocks_list}, type=str)


class PriceType(str, Enum):
    OPEN = "open"
    CLOSE = "close"
    HIGH = "high"
    LOW = "low"
    ADJ_CLOSE = "adj_close"


class DashboardConfig(BaseModel):

    class Config:
        @staticmethod
        def streamlit_label_generator(x):
            return x.replace("_", " ").title()

    # TODO: manually editing Tuple[date, date] doesn't work
    date_range: DateRange = DateRange(date(2021, 1, 1), date(2022, 12, 31))
    price_type: PriceType = "close"
    stocks: Set[Stock] = ["AAPL"]
    log_scale: bool = False
    # TODO: When validating, error message happens twice
    index_to_start_date: Optional[date] = Field(default=date(2021, 3, 2), streamlit_disabled=True)

    @validator("index_to_start_date", allow_reuse=True)
    def validate_trading_date(cls, v):
        if v is None:
            return None
        if v not in df["date"].to_numpy():
            raise ValueError("Not a valid trading date")
        return v


state_manager = StateManager(DashboardConfig)

with st.sidebar:
    st.subheader("Dashboard config")
    config = state_manager.form()
    st.markdown("---")
    state_manager.text_area()
    st.text("\0\n\n\0")  # padding


if config.index_to_start_date:
    _df = df.loc[
        df["date"] == config.index_to_start_date,
        ["ticker", "price_type", "price"]
    ].rename(columns={"price": "index_base_price"})
    df = df.merge(
        right=_df,
        on=["ticker", "price_type"],
        how="left"
    )
    df["price_index"] = df["price"] / df["index_base_price"]

df = df.loc[
    (df["price_type"] == config.price_type)
    & (df["ticker"].isin(config.stocks))
    & (df["date"] >= config.date_range[0])
    & (df["date"] <= config.date_range[1])
]


col_name = "price" if not config.index_to_start_date else "price_index"

chart = (
    alt.Chart(df)
    .mark_line()
    .encode(
        x="date:T",
        y=alt.Y(col_name, scale=alt.Scale(type="log" if config.log_scale else "linear")),
        color="ticker"
    )
)

if config.index_to_start_date:
    vertical_line_for_date = (
        alt.Chart(pd.DataFrame([{"date": config.index_to_start_date}]))
        .mark_rule()
        .encode(
            x="date"
        )
    )
    chart += vertical_line_for_date

st.altair_chart(chart, use_container_width=True)
