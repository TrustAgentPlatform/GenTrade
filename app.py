import streamlit as st
import pandas as pd

def start_trading(crypto_name:str):
    st.header(crypto_name)
    tab1, tab2 = st.tabs(['Market', 'BackTest'])

crypto_name = st.sidebar.selectbox("Choose a crypto", ["BTCUSDT", "ETHUSDT"])
start_trading(crypto_name)