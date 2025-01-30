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
from utils.apis import get_fx, get_sales_payment_journal, list_customer, list_sales_invoice, list_sales_payment, \
    get_accounts_by_type

def display_payment(payment: dict) -> dict:
    return {
        'payment_id': payment['payment_id'],
        'payment_num': payment['payment_num'],
        'payment_dt': datetime.strptime(payment['payment_dt'], '%Y-%m-%d'),
        'payment_acct_name': payment['payment_acct_name'],
        'currency': CurType(payment['currency']).name,
        'num_invoices': payment['num_invoices'],
        'gross_payment_base': payment['gross_payment_base'],
        'invoice_nums': payment['invoice_nums'],
    }

def clear_entries_from_cache():
    pass

def reset_page():
    st.session_state['validated'] = False
    
def clear_entries_and_reset_page():
    clear_entries_from_cache()
    reset_page()  
    
customers = list_customer()
dds_customers = DropdownSelect(
    briefs=customers,
    include_null=False,
    id_key='cust_id',
    display_keys=['cust_id', 'customer_name']
)
dds_currency = DropdownSelect.from_enum(
    CurType,
    include_null=False
)
ast_accts = get_accounts_by_type(acct_type=AcctType.AST.value)
lib_accts = get_accounts_by_type(acct_type=AcctType.LIB.value)
equ_accts = get_accounts_by_type(acct_type=AcctType.EQU.value)
balsh_accts = ast_accts + lib_accts + equ_accts
dds_accts = DropdownSelect(
    briefs=balsh_accts,
    include_null=False,
    id_key='acct_id',
    display_keys=['acct_name']
)


widget_cols = st.columns([1, 2])
with widget_cols[0]:
    edit_mode = st.radio(
        label='Edit Mode',
        options=['Add', 'Edit'],
        format_func=lambda o: 'Search/Edit' if o == 'Edit' else 'Add',
        # when user is in edit mode, the data will be kept in st.session_state['debit_entries]
        # when user navigate to other pages, the data will still be kepted
        # but when user navigate back to journal page, need to make sure the Edit tab is selected
        # otherwise the Add page will contain edit mode cache
        index=1,
        horizontal=True,
        on_change=clear_entries_and_reset_page, # TODO
    )

with widget_cols[1]:
    edit_customer = st.selectbox(
        label='👇 Select Customer',
        options=dds_customers.options,
        index=0
    )
    cust_id = dds_customers.get_id(edit_customer)
    
invoices = list_sales_invoice(customer_ids=[cust_id])
#st.json(invoices)

if edit_mode == 'Edit':
    payments = list_sales_payment(invoice_ids=[i['invoice_id'] for i in invoices])
    #st.json(payments)
    
    pmt_displays = map(display_payment, payments)
    selected: dict = st.dataframe(
        data=pmt_displays,
        use_container_width=True,
        hide_index=True,
        column_order=[
            'payment_num',
            'payment_dt',
            #'entity_name',
            'payment_acct_name',
            'currency',
            'num_invoices',
            'gross_payment_base',
            'invoice_nums'
        ],
        column_config={
            'payment_num': st.column_config.TextColumn(
                label='PMT Num',
                width=None,
                pinned=True
            ),
            'payment_dt': st.column_config.DateColumn(
                label='Date',
                width=None,
                pinned=True,
            ),
            'payment_acct_name': st.column_config.TextColumn(
                label='PMT Account',
                width=None,
                pinned=True,
            ),
            'currency': st.column_config.SelectboxColumn(
                label='Pay Currency',
                width=None,
                options=dds_currency.options,
                #required=True
            ),
            'num_invoices': st.column_config.NumberColumn(
                label='# Invoices',
                width=None,
                format='%d'
            ),
            'gross_payment_base': st.column_config.NumberColumn(
                label='$Gross Base',
                width=None,
                format='$ %.2f'
            ),
            'invoice_nums': st.column_config.ListColumn(
                label='Invoice Nums',
                width=None
            ),
        },
        on_select=clear_entries_from_cache, # TODO
        selection_mode=(
            'single-row',
        )
    )

    st.divider()
    
    if _row_list := selected['selection']['rows']:
        pmt_id_sel = payments[_row_list[0]]['payment_id']
        pmt_sel, jrn_sel = get_sales_payment_journal(pmt_id_sel)

        ui.badges(
            badge_list=[("Payment ID", "default"), (pmt_id_sel, "secondary")], 
            class_name="flex gap-2", 
            key="badges1"
        )
        st.json(pmt_sel)
        
# either add mode or selected edit/view mode
if edit_mode == 'Add' or (edit_mode == 'Edit' and _row_list):
    
    pmt_cols = st.columns(2)
    with pmt_cols[0]:
        pmt_num = st.text_input(
            label='#️⃣ Payment Number',
            value="" if edit_mode == 'Add' else pmt_sel['payment_num'],
            type='default', 
            placeholder="payment number here", 
        )
        pmt_date = st.date_input(
            label='📅 Invoice Date',
            value=date.today() if edit_mode == 'Add' else pmt_sel['payment_dt'],
            key=f'date_input',
            disabled=False
        )
        pmt_acct = st.selectbox(
            label='💳 Payment Account',
            options=dds_accts.options,
            key='acct_select',
            index=0 if edit_mode == 'Add' else dds_accts.get_idx_from_id(pmt_sel['payment_acct_id']),
            disabled=False
        )
        pmt_fee = st.number_input(
            label='🚚 Payment Fee',
            value=0.0 if edit_mode == 'Add' else pmt_sel['payment_fee'],
            step=0.1,
            key='fee_charge_num'
        )
        