import streamlit as st
import streamlit_shadcn_ui as ui
from utils.apis import cookie_manager, login, logout, register
st.set_page_config(layout="centered")

cols = st.columns(2, gap='large', vertical_alignment='top')

with cols[0]:
    st.image("images/app_logo.png")
    st.caption("Manage your financials all in one place")

with cols[1]:
    tabs = st.tabs(['Login', 'Register'])
    with tabs[0]:
        
        login_cont = st.container(key="login_cont", border=False)
        if not cookie_manager.get("authenticated"):
            
            login_cont.title("🎉Login")
        
            username = login_cont.text_input("User Name", key="username", icon='🐮')
            password = login_cont.text_input("Password", key="password", type="password", icon='🔒', max_chars=20)
            
            if login_cont.button(
                "Login", 
                key="login_button", 
                type='tertiary', 
                icon=":material/login:"
            ):
                if login(username, password):
                    login_cont.success("Login successful", icon='💯')
                    # TODO: refresh the page
                else:
                    login_cont.error("Invalid username or password", icon='🙊')
        else:
            login_cont.info(f"Login successful, welcome back **{cookie_manager.get('username')}**", icon='🥳')
            if login_cont.button(
                "Logout", 
                key="logout_button",
                type='tertiary', 
                icon=":material/logout:"
            ):
                logout()
                st.rerun()
                
    with tabs[1]:
        register_cont = st.container(key="register_cont", border=False)
        register_cont.title("🎊Register")
        
        username = register_cont.text_input(
            "User Name", 
            key="reg_username", 
            icon='🦁'
        )
        password = register_cont.text_input(
            "Password", 
            key="reg_password", 
            type="password", 
            icon='🔒', 
            max_chars=20
        )
        confirm_password = register_cont.text_input(
            "Confirm Password", 
            key="reg_confirm_password", 
            type="password", 
            icon='🔒', 
            max_chars=20
        )
        if register_cont.button(
            "Register", 
            key="register_button",
            type='tertiary', 
            icon=":material/person_add:"
        ):
            if password == confirm_password:
                if register(username, password):
                    register_cont.success("Registration successful", icon='💯')
                else:
                    register_cont.error("Registration failed", icon='⁉️')
            else:
                register_cont.error("Passwords do not match", icon='🙊')
        