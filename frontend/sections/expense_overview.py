from datetime import date, datetime, timedelta
import uuid
from itertools import cycle
import streamlit as st
import streamlit_shadcn_ui as ui
from utils.enums import CurType
from utils.apis import summary_expense, get_base_currency, get_comp_contact, get_logo

st.set_page_config(layout="centered")
with st.sidebar:
    comp_name, _ = get_comp_contact()
    
    st.markdown(f"Hello, :rainbow[**{comp_name}**]")
    st.logo(get_logo(), size='large')
    
    
def process_exp_for_barchart(exps: list[dict]) -> list[dict]:
    colors = cycle(['#f77189', '#e68332', '#bb9832', '#97a431', '#50b131', '#34af84', '#36ada4', '#38aabf', '#3ba3ec', '#a48cf4', '#e866f4', '#f668c2'])
    #total = sum(e['total_base_amount'] for e in exps)
    r = []
    for i, e in enumerate(exps):
        r.append({
            'expense_type': str(i + 1).zfill(2) + " - " + e['expense_type'],
            "total_base_amount": e['total_base_amount'],
            #"percentage": e['total_base_amount'] / total,
            "color": next(colors)
        })
    return r

current_dt = datetime.now().date()
ytd_exp = summary_expense(current_dt.replace(month=1, day=1), current_dt)
mtd_exp = summary_expense(current_dt.replace(day=1), current_dt)
base_cur = get_base_currency()

st.subheader('Summary')

exp_cols = st.columns(2, gap='small', border=False)
with exp_cols[0]:
    ytd_exp_total = sum(e['total_base_amount'] for e in ytd_exp)
    ui.metric_card(
        title="YTD Expense", 
        content=f"{CurType(base_cur).name} {ytd_exp_total:,.2f}", 
        description=f"As of {date.today()}", 
        key=str(uuid.uuid4())
    )
    if len(ytd_exp) == 0:
        st.warning("No expense found during the year", icon='🥵')
    else:
        st.bar_chart(
            data=process_exp_for_barchart(ytd_exp),
            x='expense_type',
            y='total_base_amount',
            x_label='Expense',
            y_label=f'Amount ({CurType(base_cur).name})',
            color='color',
            horizontal=True,
            use_container_width=True
        )
    
with exp_cols[1]:
    mtd_exp_total = sum(e['total_base_amount'] for e in mtd_exp)
    ui.metric_card(
        title="MTD Expense", 
        content=f"{CurType(base_cur).name} {mtd_exp_total:,.2f}", 
        description=f"As of {date.today()}", 
        key=str(uuid.uuid4())
    )
    if len(mtd_exp) == 0:
        st.warning("No expense found during the month", icon='🥵')
    else:
        st.bar_chart(
            data=process_exp_for_barchart(mtd_exp),
            x='expense_type',
            y='total_base_amount',
            x_label='Expense',
            y_label=f'Amount ({CurType(base_cur).name})',
            color='color',
            horizontal=True,
            use_container_width=True
        )
        

st.subheader('Query Expense')
qry_cols = st.columns(2, border=False)
with qry_cols[0]:
    start_dt = st.date_input(
        label='Start Date',
        value=current_dt.replace(month=1, day=1),
        key='dt_start'
    )
with qry_cols[1]:
    end_dt = st.date_input(
        label='End Date',
        value=current_dt,
        key='dt_end'
    )

qry_exp = summary_expense(start_dt, end_dt)
qry_exp_total = sum(e['total_base_amount'] for e in qry_exp)
if len(qry_exp) == 0:
    st.warning("No expense found during the selected period", icon='🥵')
else:

    st.markdown(f"**Total Expense ({CurType(base_cur).name})**: :violet-background[{qry_exp_total:.2f}]")
    st.bar_chart(
        data=process_exp_for_barchart(qry_exp),
        x='expense_type',
        y='total_base_amount',
        x_label='Expense',
        y_label=f'Amount ({CurType(base_cur).name})',
        color='color',
        horizontal=True,
        use_container_width=True
    )