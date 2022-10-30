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
