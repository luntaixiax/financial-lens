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
from utils.apis import get_base_currency, list_supplier, list_purchase_invoice, \
    list_purchase_payment, get_ppurchase_invoices_balance_by_entity, get_comp_contact, get_logo

st.set_page_config(layout="centered")
with st.sidebar:
    comp_name, _ = get_comp_contact()
    
    st.markdown(f"Hello, :rainbow[**{comp_name}**]")
    st.logo(get_logo(), size='large')
    
    
def get_purchase_payment_hist() -> list[dict]:
    invoices = list_purchase_invoice(supplier_ids=[supplier_id])
    payments = list_purchase_payment(invoice_ids=[i['invoice_id'] for i in invoices])
    
    chain = []
    for invoice in invoices:    
        chain.append({
            'direction': 'invoice',
            'trans_num': invoice['invoice_num'],
            'trans_dt': invoice['invoice_dt'],
            'currency': invoice['currency'],
            'raw_amount': invoice['total_raw_amount'],
            'base_amount': invoice['total_base_amount']
        })
    
    for payment in payments:    
        chain.append({
            'direction': 'payment',
            'trans_num': payment['payment_num'],
            'trans_dt': payment['payment_dt'],
            'currency': payment['currency'],
            'raw_amount': payment['gross_payment_raw'],
            'base_amount': payment['gross_payment_base'],
        })
        
    return sorted(chain, key=lambda x: x['trans_dt'], reverse=True)
        


suppliers = list_supplier()
if len(suppliers) > 0:

    dds_suppliers = DropdownSelect(
        briefs=suppliers,
        include_null=False,
        id_key='supplier_id',
        display_keys=['supplier_id', 'supplier_name']
    )

    edit_supplier = st.selectbox(
        label='👇 Select Customer',
        options=dds_suppliers.options,
        index=0
    )
    supplier_id = dds_suppliers.get_id(edit_supplier)

    balances = get_ppurchase_invoices_balance_by_entity(
        entity_id=supplier_id,
        bal_dt=date.today()
    )

    st.subheader("Outstanding Invoices")
    if len(balances) > 0:
        balances_display = pd.DataFrame.from_records([
            {
                'Invoice ID': b['invoice_id'],
                'Currency': CurType(b['currency']).name,
                'Amount Billed': round(b['raw_amount'], 2),
                'Amount Paid': round(b['paid_amount'], 2),
                'Balance': round(b['balance'], 2),
                
            } for b in balances
        ])
        balances_display = balances_display[balances_display['Balance'] != 0]

        ui.table(balances_display)
        
    else:
        st.info("All Invoices cleared!", icon='👏')

    st.subheader("Transactions")

    historys = get_purchase_payment_hist()

    total_billed = sum(h['base_amount'] for h in historys if h['direction'] == 'invoice')
    num_billed = sum(1 for h in historys if h['direction'] == 'invoice')
    total_paid = sum(h['base_amount'] for h in historys if h['direction'] == 'payment')
    num_paid = sum(1 for h in historys if h['direction'] == 'payment')
    total_balance = total_billed - total_paid
    base_currency = CurType(get_base_currency()).name

    card_cols = st.columns(3)
    with card_cols[0]:
        ui.metric_card(
            title="Total Invoiced", 
            content=f"{base_currency} {total_billed: .2f}", 
            description=f"# invoice: {num_billed}", 
            key="card1"
        )
    with card_cols[1]:
        ui.metric_card(
            title="Total Paid", 
            content=f"{base_currency} {total_paid: .2f}", 
            description=f"# payment: {num_paid}", 
            key="card2"
        )
    with card_cols[2]:
        ui.metric_card(
            title="Remaining Balance", 
            content=f"{base_currency} {total_balance: .2f}", 
            description=f"equivalent in base currency", 
            key="card3"
        )

    for history in historys:
        dt_display = datetime.strptime(history['trans_dt'], '%Y-%m-%d').strftime('%b %d, %Y')
        if history['direction'] == 'invoice':
            label = f"{dt_display} | **:red-background[invoice]**"
            disp = {
                'Invoice #': history['trans_num'],
                'Currency': CurType(history['currency']).name,
                'Amount': round(history['raw_amount'], 2)
            }
        else:
            label = f"{dt_display} | **:green-background[payment]**"
            disp = {
                'Payment #': history['trans_num'],
                'Currency': CurType(history['currency']).name,
                'Amount': round(history['raw_amount'], 2)
            }
        
        with st.expander(label=label, expanded=True):
            
            ui.table(pd.DataFrame.from_records([disp]))
            
else:
    st.warning("No Customer found, must create supplier to show purchase", icon='🥵')