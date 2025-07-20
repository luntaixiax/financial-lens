import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit_nested_layout # need it for nested structure
import pandas as pd
from utils.enums import CurType, AcctType
from utils.apis import tree_balance_sheet, get_base_currency, get_comp_contact, get_logo
from utils.tools import DropdownSelect
from utils.apis import cookie_manager

st.set_page_config(layout="wide")
if cookie_manager.get("authenticated") != True:
    st.switch_page('sections/login.py')
access_token=cookie_manager.get("access_token")

with st.sidebar:
    comp_name, _ = get_comp_contact(access_token=access_token)
    
    st.markdown(f"Hello, :rainbow[**{comp_name}**]")
    st.logo(get_logo(access_token=access_token), size='large')
    
st.subheader('Balance Sheet')

base_cur = get_base_currency(access_token=access_token)

def show_expander(tree: dict, icon: str):
    net_base = f"({CurType(base_cur).name}) {tree['chart_summary']['net_base']: ,.2f}"
    label = f"**{tree['name']}** &nbsp; | &nbsp; :violet-background[{net_base}]"
    with st.expander(label=label, expanded=True, icon = icon):
        st.empty()
        accts = tree['acct_summary']
        accts = pd.DataFrame.from_records([
            {
                'Acct Name': r['acct_name'], 
                'Raw Amount': f"{CurType(r['currency']).name} {r['net_raw']: ,.2f}",
                f"Base Amount ({CurType(base_cur).name})": f"{r['net_base']: ,.2f}"
            } 
            for r in accts
        ])
        if not accts.empty:
            ui.table(accts)
        if 'children' in tree:
            for child in tree['children']:
                show_expander(child, icon)

cols = st.columns(3)
with cols[0]:
    # add dropdown for date
    rep_dt = st.date_input(
        label='As of Reporting Date'
    )

bal_sh = tree_balance_sheet(rep_dt=rep_dt, access_token=access_token)

cols = st.columns(2)
with cols[0]:
    total_ass = bal_sh[str(AcctType.AST.value)]['chart_summary']['net_base']
    st.markdown(f"**Total Asset :green-background[({CurType(base_cur).name}) {total_ass:,.2f}]**")   
    show_expander(bal_sh[str(AcctType.AST.value)], icon='🏘️')
    st.markdown(f'📥 **Total Asset ({CurType(base_cur).name})**: :grey-background[{total_ass:,.2f}]')

with cols[1]:
    total_lib = bal_sh[str(AcctType.LIB.value)]['chart_summary']['net_base']
    total_equ = bal_sh[str(AcctType.EQU.value)]['chart_summary']['net_base']
    
    
    st.markdown(f"**Total Liability :orange-background[({CurType(base_cur).name}) {total_lib:,.2f}]**")
    show_expander(bal_sh[str(AcctType.LIB.value)], icon='💳')
    st.markdown(f"**Total Equity :blue-background[({CurType(base_cur).name}) {total_equ:,.2f}]**")
    show_expander(bal_sh[str(AcctType.EQU.value)], icon='💸')
    
    
    st.markdown(f'📥 **Total Equity+Liability ({CurType(base_cur).name})**: :grey-background[{total_lib+total_equ:,.2f}]')