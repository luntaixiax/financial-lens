import streamlit as st
import json

from utils.base import get_req, post_req, put_req, delete_req

with st.form(key='api', clear_on_submit=True):
    method = st.selectbox(
        label = 'Method',
        options = ['GET', 'POST', 'PUT', 'DELETE']
    )
    prefix = st.selectbox(
        label = 'Prefix',
        options = ['entity', 'accounts', 'journal', 'item', 'sales', 'purchase', 'expense']
    )
    endpoint = st.text_input(
        label = 'Endpoint'
    )
    params = st.text_area(
        label='Parameter Dict'
    )
    body = st.text_area(
        label='Body Dict'
    )
    
    submitted = st.form_submit_button("Submit")
    if submitted:

        if params == "":
            params = None
        else:
            params = json.loads(params)
            st.text('params')
            st.json(params)
            
        if body == "":
            body = None
        else:
            body = json.loads(body)
            st.text('body')
            st.json(body)
            
        if method == 'GET':
            try:
                result = get_req(prefix, endpoint, params, body)
            except Exception as e:
                st.error(e)
            else:
                st.json(result)
                
        elif method == 'POST':
            try:
                result = post_req(prefix, endpoint, params, body)
            except Exception as e:
                st.error(e)
            else:
                st.json(result)

        elif method == 'PUT':
            try:
                result = put_req(prefix, endpoint, params, body)
            except Exception as e:
                st.error(e)
            else:
                st.json(result)
        
        elif method == 'DELETE':
            try:
                result = delete_req(prefix, endpoint, params, body)
            except Exception as e:
                st.error(e)
            else:
                st.json(result)
                
import streamlit as st
import pandas as pd

# Initial DataFrame
df = pd.DataFrame([
    {"name": "Alice", "edited": False, "input": 0, "result": 0},
    {"name": "Bob", "edited": False, "input": 0, "result": 0},
    {"name": "Cecil", "edited": False, "input": 0, "result": 0},
])

# Function to handle changes in the DataFrame
def df_on_change():
    state = st.session_state["df_editor"]
    print(state)
    for index, updates in state["edited_rows"].items():
        st.session_state["df"].loc[st.session_state["df"].index == index, "edited"] = True
        for key, value in updates.items():
            st.session_state["df"].loc[st.session_state["df"].index == index, key] = value
        # Update the result column based on the input column
        st.session_state["df"].loc[st.session_state["df"].index == index, "result"] = (
            st.session_state["df"].loc[st.session_state["df"].index == index, "input"] * 3
        )

# Main editor function
#def editor():
if "df" not in st.session_state:
    st.session_state["df"] = df
st.data_editor(
    st.session_state["df"],
    key="df_editor",
    on_change=df_on_change,
    num_rows='dynamic'
)

# Run the editor
#editor()
