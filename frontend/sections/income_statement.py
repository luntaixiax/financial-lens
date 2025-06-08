import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit_nested_layout # need it for nested structure
import pandas as pd
from utils.enums import CurType, AcctType
from utils.apis import tree_income_statement, get_base_currency, get_comp_contact, get_logo
from utils.tools import DropdownSelect

st.set_page_config(layout="wide")
with st.sidebar:
    comp_name, _ = get_comp_contact()
    
    st.markdown(f"Hello, :rainbow[**{comp_name}**]")
    st.logo(get_logo(), size='large')
    
    
st.subheader('Income Statement')

base_cur = get_base_currency()

def show_expander(tree: dict, icon: str):
    net_base = f"({CurType(base_cur).name}) {tree['chart_summary']['net_base']: ,.2f}"
    label = f"**{tree['name']}** &nbsp; | &nbsp; :violet-background[{net_base}]"
    with st.expander(label=label, expanded=True, icon = icon):
        st.empty()
        accts = tree['acct_summary']
        accts = pd.DataFrame.from_records([
            {
                'Acct Name': r['acct_name'], 
                f"Base Amount ({CurType(base_cur).name})": f"{r['net_base']: ,.2f}"
            } 
            for r in accts
        ])
        if not accts.empty:
            ui.table(accts)
        if 'children' in tree:
            for child in tree['children']:
                show_expander(child, icon)

cols = st.columns(4)
with cols[0]:
    # add dropdown for date
    start_dt = st.date_input(
        label='Start Rep Date',
        key='dt_start'
    )
with cols[1]:
    # add dropdown for date
    end_dt = st.date_input(
        label='End Rep Date',
        key='dt_end'
    )

inc_st = tree_income_statement(start_dt=start_dt, end_dt=end_dt)

cols = st.columns(2)
with cols[0]:
    st.markdown(f"**Income**")
    show_expander(inc_st[str(AcctType.INC.value)], icon='🤑')
    
with cols[1]:
    st.markdown(f"**Expense**")
    show_expander(inc_st[str(AcctType.EXP.value)], icon='🛒')

total_inc = inc_st[str(AcctType.INC.value)]['chart_summary']['net_base']
total_exp = inc_st[str(AcctType.EXP.value)]['chart_summary']['net_base']
net_inc = total_inc - total_exp
st.markdown(f'📥 **Total Income ({CurType(get_base_currency()).name})**: :green-background[{total_inc:,.2f}]')
st.markdown(f'📤 **Total Expense ({CurType(get_base_currency()).name})**: :blue-background[{total_exp:,.2f}]')
st.markdown(f'📤 **Net Income ({CurType(get_base_currency()).name})**: :orange-background[{net_inc:,.2f}]')