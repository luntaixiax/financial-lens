import math
import time
import io
import uuid
import streamlit as st
import streamlit_shadcn_ui as ui
from utils.apis import set_logo, get_logo
    
st.set_page_config(layout="centered")

logo_cols = st.columns([1, 4])
with logo_cols[1]:
    logo = st.file_uploader(
        label='Your Company LOGO',
        accept_multiple_files=False,
    )
    if logo is not None:
        bytes_logo = io.BufferedReader(logo)
        set_logo(bytes_logo)

with logo_cols[0]:
    st.image(get_logo())
    
