import requests
import streamlit as st
import extra_streamlit_components as stx
from utils.apis import cookie_manager, login, logout

cookies = cookie_manager.get_all()
st.write(cookies)


# def login(username: str, password: str):
#     try:
#         BACKEND_URL = "http://localhost:8181"
#         response = requests.post(
#             f"{BACKEND_URL}/api/v1/management/login",
#             data={
#                 "username": username,
#                 "password": password
#             },
#             headers={"Content-Type": "application/x-www-form-urlencoded"}
#         )
        
#         if response.status_code == 200:
#             token_data = response.json()
#             cookie_manager.set("authenticated", True, key='authenticated_set')
#             cookie_manager.set("username", username, key='username_set')
#             cookie_manager.set("access_token", token_data["access_token"], key='access_token_set')
#             return True
#         else:
#             st.error(f"Login failed: {response.text}")
#             return False
            
#     except requests.exceptions.RequestException as e:
#         st.error(f"Connection error: {e}")
#         return False
    
if not cookie_manager.get("authenticated"):
    username = st.text_input("username", key="username")
    password = st.text_input("password", key="password", type="password")
    
    if st.button("Login", key="login_button"):
        if login(username, password):
            st.success("Login successful")
            # TODO: refresh the page
        else:
            st.error("Invalid username or password")
else:
    st.info(f"Login successful, welcome back {cookie_manager.get('username')}")
    if st.button("Logout", key="logout_button"):
        logout()
        st.rerun()
