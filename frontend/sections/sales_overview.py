import math
import time
import uuid
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit.components.v1 as components
from datetime import datetime, date, timedelta
from utils.tools import DropdownSelect
from utils.enums import AcctType, CurType, EntityType, EntryType, ItemType, JournalSrc, UnitType
from utils.apis import get_base_currency, list_customer, list_sales_invoice, list_sales_payment, \
    get_psales_invoices_balance_by_entity, get_comp_contact, get_logo
from utils.apis import cookie_manager

st.set_page_config(layout="centered")
if cookie_manager.get("authenticated") != True:
    st.switch_page('sections/login.py')
access_token=cookie_manager.get("access_token")

with st.sidebar:
    comp_name, _ = get_comp_contact(access_token=access_token)
    
    st.markdown(f"Hello, :rainbow[**{comp_name}**]")
    st.logo(get_logo(access_token=access_token), size='large')
    
def get_sales_payment_hist() -> list[dict]:
    invoices = list_sales_invoice(customer_ids=[cust_id])
    payments = list_sales_payment(invoice_ids=[i['invoice_id'] for i in invoices])
    
    chain = []
    for invoice in invoices:    
        chain.append({
            'direction': 'invoice',
            'trans_id': invoice['invoice_id'],
            'trans_num': invoice['invoice_num'],
            'trans_dt': invoice['invoice_dt'],
            'currency': invoice['currency'],
            'raw_amount': invoice['total_raw_amount'],
            'base_amount': invoice['total_base_amount']
        })
    
    for payment in payments:    
        chain.append({
            'direction': 'payment',
            'trans_id': payment['payment_id'],
            'trans_num': payment['payment_num'],
            'trans_dt': payment['payment_dt'],
            'currency': payment['currency'],
            'raw_amount': payment['gross_payment'],
            'base_amount': payment['gross_payment_base'],
            'offset_amount': payment['accrual_offset_base'],
            'invoice_nums': payment['invoice_num_strs']
        })
        
    return sorted(chain, key=lambda x: x['trans_dt'], reverse=True)
        


customers = list_customer(access_token=access_token)
if len(customers) > 0:

    dds_customers = DropdownSelect(
        briefs=customers,
        include_null=False,
        id_key='cust_id',
        display_keys=['cust_id', 'customer_name']
    )

    edit_customer = st.selectbox(
        label='👇 Select Customer',
        options=dds_customers.options,
        index=0
    )
    cust_id = dds_customers.get_id(edit_customer)
    
    # display metrics
    historys = get_sales_payment_hist()

    total_billed = sum(h['base_amount'] for h in historys if h['direction'] == 'invoice')
    num_billed = sum(1 for h in historys if h['direction'] == 'invoice')
    total_paid = sum(h['base_amount'] for h in historys if h['direction'] == 'payment')
    num_paid = sum(1 for h in historys if h['direction'] == 'payment')
    total_offset = sum(h['offset_amount'] for h in historys if h['direction'] == 'payment')
    total_balance = total_billed - total_offset
    fx_gain = total_paid - total_offset
    base_currency = CurType(get_base_currency()).name

    card_cols = st.columns(3)
    with card_cols[0]:
        ui.metric_card(
            title="Total Invoiced", 
            content=f"{base_currency} {total_billed: ,.2f}", 
            description=f"# invoice: {num_billed}", 
            key="card1"
        )
    with card_cols[1]:
        ui.metric_card(
            title="Total Paid", 
            content=f"{base_currency} {total_paid: ,.2f}", 
            description=f"# payment: {num_paid}", 
            key="card2"
        )
    with card_cols[2]:
        ui.metric_card(
            title="Total Offset", 
            content=f"{base_currency} {total_offset: ,.2f}", 
            description=f"offset in A/R", 
            key="card3"
        )
        
    card_cols2 = st.columns(2)
    with card_cols2[0]:
        ui.metric_card(
            title="Remaining Balance", 
            content=f"{base_currency} {total_balance: ,.2f}", 
            description=f"equivalent in base currency", 
            key="card4"
        )
    with card_cols2[1]:
        ui.metric_card(
            title="FX Gain/Loss", 
            content=f"{base_currency} {fx_gain: ,.2f}", 
            description=f"between invoice and payment", 
            key="card5"
        )

    tabs = st.tabs(['Oustanding Invoices', 'Transaction History'])
    
    with tabs[0]:
        balances = get_psales_invoices_balance_by_entity(
            entity_id=cust_id,
            bal_dt=date.today()
        )

        st.subheader("Outstanding Invoices")
        if len(balances) > 0:
            balances_display = pd.DataFrame.from_records([
                {
                    'Invoice #': b['invoice_num'],
                    'Currency': CurType(b['currency']).name,
                    'Amount Billed': round(b['raw_amount'], 2),
                    'Amount Paid': round(b['paid_amount'], 2),
                    'Balance': round(b['balance'], 2),
                    
                } for b in balances
            ])
            balances_display = balances_display[balances_display['Balance'] != 0]

            st.markdown(f"As of :blue[{date.today().strftime('%b %d, %Y')}]")
            ui.table(balances_display)
            
        else:
            st.info("All Invoices cleared!", icon='👏')

    with tabs[1]:
        with st.container(height=1000, border=True):
            for history in historys:
                dt_display = datetime.strptime(history['trans_dt'], '%Y-%m-%d').strftime('%b %d, %Y')
                if history['direction'] == 'invoice':
                    label = f"**{dt_display}** | **:red-background[invoice]** | :grey-background[{history['trans_id']}]"
                    disp = {
                        'Invoice #': history['trans_num'],
                        'Currency': CurType(history['currency']).name,
                        'Amount': round(history['raw_amount'], 2)
                    }
                else:
                    label = f"**{dt_display}** | **:green-background[payment]** | :grey-background[{history['trans_id']}]"
                    disp = {
                        'Payment #': history['trans_num'],
                        'Against Invoices': history['invoice_nums'],
                        'Currency': CurType(history['currency']).name,
                        'Amount': round(history['raw_amount'], 2)
                    }
                    
                if datetime.strptime(history['trans_dt'], '%Y-%m-%d').date() > date.today():
                    icon = '⌛'
                else:
                    icon = '☑️'
                
                with st.expander(label=label, expanded=True, icon=icon):
                    
                    ui.table(pd.DataFrame.from_records([disp]))
            
else:
    st.warning("No Customer found, must create customer to show sales", icon='🥵')