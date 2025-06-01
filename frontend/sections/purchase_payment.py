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
from utils.apis import get_account, get_fx, get_purchase_payment_journal, list_supplier, list_purchase_invoice, list_purchase_payment, \
    get_accounts_by_type, get_purchase_invoice_balance, validate_purchase_payment, create_journal_from_new_purchase_payment, \
    get_base_currency, get_all_accounts, add_purchase_payment, update_purchase_payment, delete_purchase_payment

st.set_page_config(layout="centered")

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
    if 'pmt_items' in st.session_state:
        del st.session_state['pmt_items']
    if 'journal' in st.session_state:
        del st.session_state['journal']

def reset_validate():
    st.session_state['validated'] = False
    
def reset_page():
    reset_validate()
    if 'journal' in st.session_state:
        del st.session_state['journal']
    
def clear_entries_and_reset_page():
    clear_entries_from_cache()
    reset_page()  
    
def on_change_pmt_items():
    # whenever edited the table
    reset_validate()
    
    # get changes from data editor
    state = st.session_state['key_editor_pmt_items']
    
    # edit
    for index, updates in state["edited_rows"].items():
        st.session_state['pmt_items'][index].update(updates)
    # add new row
    for new_row in state["added_rows"]:
        st.session_state['pmt_items'].append(new_row)
    # delete row TODO: which comes first, add or delete
    for idx in sorted(state["deleted_rows"], reverse=True):
        # need to reversly delete, bc delete on update will get out of range error
        st.session_state['pmt_items'].pop(idx)
        
    for i, e in enumerate(st.session_state['pmt_items']):
        new_e = update_pmt_item(e)
        # edit
        for k, v in new_e.items():
            st.session_state['pmt_items'][i][k] = v
            
def update_pmt_item(entry: dict) -> dict:
    if (inv_num := entry.get('invoice_num')) is not None:
        inv_id = dds_invs.get_id(inv_num)
        balance = get_purchase_invoice_balance(inv_id, pmt_date)
        entry['balance'] = balance['balance']
        
        # add paid amount in payment currency
        if (payment_amount := entry.get('payment_amount')) is not None:
            if (payment_amount_raw := entry.get('payment_amount_raw')) is None: # only if null
                entry['payment_amount_raw'] = payment_amount * get_fx(
                    src_currency=CurType(pmt_acct['currency']).value,
                    tgt_currency=CurType(balance['currency']).value,
                    cur_dt=pmt_date
                )

    return entry

def convert_pmt_items_to_db(entries: list[dict]) -> list[dict]:
    items = []
    for e in entries:
        if e.get('invoice_num') is None:
            continue
        if e.get('payment_amount') is None:
            continue
        if e.get('payment_amount_raw') is None:
            continue
        
        r = {}
        r['invoice_id'] = dds_invs.get_id(e.get('invoice_num'))
        r['payment_amount'] = e['payment_amount']
        r['payment_amount_raw'] = e['payment_amount_raw']
        
        items.append(r)
    return items
    
def validate_payment(payment_: dict):
    # TODO: get back validated invoice with computed field and write to st.session_state for display
    # at least have 1 item
    if len(payment_['payment_items']) < 1:
        ui.alert_dialog(
            show=True, # TODO
            title="At least have one payment item",
            description='Have no items defined',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    # detect if payment key info is missing
    if payment_['payment_num'] in (None, ""):
        ui.alert_dialog(
            show=True, # TODO
            title="Payment Number is missing",
            description='Must assign a payment number',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    if payment_['payment_dt'] is None:
        ui.alert_dialog(
            show=True, # TODO
            title="Payment Date is missing",
            description='Must assign a payment date',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    if payment_['payment_acct_id'] in (None, ""):
        ui.alert_dialog(
            show=True, # TODO
            title="Receiving Account is missing",
            description='Must assign a receiving account',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    payment_ = validate_purchase_payment(payment_)
    if isinstance(payment_, dict):
        if payment_.get('payment_items') is not None:
            st.session_state['validated'] = True
            
            # calculate and journal to session state
            jrn_ = create_journal_from_new_purchase_payment(payment_)
            st.session_state['journal'] = jrn_


class JournalEntryHelper:
    def __init__(self, journal: dict):
        self._jrn = journal
        self.debit_entries = self.get_entries(EntryType.DEBIT)
        self.credit_entries = self.get_entries(EntryType.CREDIT)
        
    def get_entries(self, entry_type: EntryType) -> list[dict]:
        return [
            {
                #'entry_id': e['entry_id'],
                #'entry_type': e['entry_type'],
                #'acct_id': e['acct']['acct_id'], # should get from options
                'acct_name': e['acct']['acct_name'],
                'currency': CurType(e['acct']['currency']).name if e['acct']['acct_type'] in (1, 2, 3) else CurType(e['cur_incexp']).name, # balance sheet item
                'amount': e['amount'],
                'amount_base': e['amount_base'],
                'description': e['description']
            }
            for e in self._jrn['entries']
            if e['entry_type'] == entry_type.value
        ]
        
        
suppliers = list_supplier()

if len(suppliers) > 0:
    dds_suppliers = DropdownSelect(
        briefs=suppliers,
        include_null=False,
        id_key='supplier_id',
        display_keys=['supplier_id', 'supplier_name']
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

    all_accts = get_all_accounts()
    dds_all_accts = DropdownSelect(
        briefs=all_accts,
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
        edit_supplier = st.selectbox(
            label='👇 Select Customer',
            options=dds_suppliers.options,
            index=0
        )
        supplier_id = dds_suppliers.get_id(edit_supplier)
        
    invoices = list_purchase_invoice(supplier_ids=[supplier_id])
    invs_options = [
        {
            'invoice_id': i['invoice_id'],
            'invoice_num': i['invoice_num'],
            'raw_amount': f"{CurType(i['currency']).name} {i['total_raw_amount']:.2f}"
        }
        for i in invoices
    ]
    dds_invs = DropdownSelect(
        briefs=invs_options,
        include_null=False,
        id_key='invoice_id',
        display_keys=['invoice_num', 'raw_amount']
    )

    if edit_mode == 'Edit':
        payments = list_purchase_payment(invoice_ids=[i['invoice_id'] for i in invoices])
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
                #'num_invoices',
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
            pmt_sel, jrn_sel = get_purchase_payment_journal(pmt_id_sel)

            ui.badges(
                badge_list=[("Payment ID", "default"), (pmt_id_sel, "secondary")], 
                class_name="flex gap-2", 
                key="badges1"
            )
            
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
                label='📅 Payment Date',
                value=date.today() if edit_mode == 'Add' else pmt_sel['payment_dt'],
                key=f'date_input',
                disabled=False,
                on_change=reset_validate
            )
        
        with pmt_cols[1]:
            ref_num = st.text_input(
                label='#️⃣ Reference Number',
                value="" if edit_mode == 'Add' else pmt_sel['ref_num'],
                type='default', 
                placeholder="reference number here", 
            )
            pmt_acct = st.selectbox(
                label='💳 Receiving Account',
                options=dds_accts.options,
                key='acct_select',
                index=0 if edit_mode == 'Add' else dds_accts.get_idx_from_id(pmt_sel['payment_acct_id']),
                disabled=False,
                on_change=reset_validate
            )
            # get payment acct details
            pmt_acct_id = dds_accts.get_id(pmt_acct)
            pmt_acct = get_account(pmt_acct_id)
            
        # prepare data editor
        if edit_mode == 'Edit':
            pmt_items = [
                {
                    'invoice_num': dds_invs._mappings.get(pi['invoice_id']),
                    'balance': get_purchase_invoice_balance(pi['invoice_id'], pmt_date)['balance'],
                    'payment_amount': pi['payment_amount'],
                    'payment_amount_raw': pi['payment_amount_raw']
                    
                } for pi in pmt_sel['payment_items']
            ]
            column_order=[
                'invoice_num',
                'payment_amount_raw',
                'payment_amount',
                #'balance', # balance is after make payment
            ]
            
            if not 'journal' in st.session_state:
                st.session_state['journal'] = jrn_sel
        else:
            pmt_items = [{c: None for c in [
                'invoice_num',
                'balance',
                'payment_amount_raw',
                'payment_amount',
            ]}]
            column_order=[
                'invoice_num',
                'balance', # balance is before make payment
                'payment_amount',
                'payment_amount_raw',
            ]
        
        if 'pmt_items' not in st.session_state:
            st.session_state['pmt_items'] = pmt_items
            
        # payment items
        pmt_item_container = st.container(border=True)
        pmt_item_container.subheader('Payment Items')
        pmt_item_entries = pmt_item_container.data_editor(
            #data=st.session_state['invoice_item_entries'], # TODO
            data=st.session_state['pmt_items'],
            num_rows='dynamic',
            use_container_width=True,
            column_order=column_order,
            column_config={
                'invoice_num': st.column_config.SelectboxColumn(
                    label='Invoice',
                    width=None,
                    options=dds_invs.options,
                    #required=True
                ),
                'balance': st.column_config.NumberColumn(
                    label="Balance (Inv Cur)",
                    width=None,
                    format='$ %.2f',
                    step=0.01,
                    disabled=True
                    #required=True
                ),
                'payment_amount_raw': st.column_config.NumberColumn(
                    label="Credit Amount (Inv Cur)",
                    width=None,
                    format='$ %.2f',
                    step=0.01,
                    disabled=False
                    #required=True
                ),
                'payment_amount': st.column_config.NumberColumn(
                    label=f"Amount Paid ({CurType(pmt_acct['currency']).name})",
                    width=None,
                    format='$ %.2f',
                    step=0.01,
                    disabled=False
                    #required=True
                ),
            },
            hide_index=True,
            key='key_editor_pmt_items',
            disabled=False,
            on_change=on_change_pmt_items,
        )
        
        pmt_cols = st.columns(2)
        with pmt_cols[0]:
            total_paid = sum(e['payment_amount'] or 0 for e in pmt_item_entries)
            st.markdown(f"📐 **Total Amount Paid ({CurType(pmt_acct['currency']).name})**: {total_paid: .2f}")
        
            pmt_fee = st.number_input(
                label=f"🚚 Bank Charge ({CurType(pmt_acct['currency']).name})",
                value=0.0 if edit_mode == 'Add' else pmt_sel['payment_fee'],
                step=0.01,
                key='fee_charge_num',
                on_change=reset_validate
            )
            
            st.markdown(f"📐 **Total Amount Received ({CurType(pmt_acct['currency']).name})**: {total_paid - pmt_fee: .2f}")
        
        with pmt_cols[1]:
            note = st.text_area(
                label='📝 Note',
                value="" if edit_mode == 'Add' else pmt_sel['note'],
                placeholder="payment note here",
                height=120
            )
            
        payment_ = {
            #"payment_id": "string",
            "payment_num": pmt_num,
            "payment_dt": pmt_date.strftime('%Y-%m-%d'), # convert to string
            "entity_type": 1, # supplier
            "payment_items": convert_pmt_items_to_db(pmt_item_entries),
            "payment_acct_id": pmt_acct_id,
            "payment_fee": pmt_fee,
            "ref_num": ref_num,
            "note": note
        }
        
        # TODO: only validate if in add mode or if in edit mode and actually changed something
        validate_btn = st.button(
            label='Validate and Update Journal Entry Preview',
            on_click=validate_payment,
            args=(payment_, )
        )
        
        
        if (edit_mode == 'Add' and st.session_state.get('validated', False)) or edit_mode == 'Edit':
            # display only in 2 scenarios:
            # 1. if add mode, but be validated (otherwise will be void)
            # 2. if edit mode, must display whether been updated or not
            with st.expander(label='Journal Entries', expanded=True, icon='📔'):
                st.subheader("Journal Entries")
                if st.session_state.get('validated', False):
                    # if validated (clicked validate button), display ad-hoc calculated journal
                    # regardless of whether it is in add or edit mode
                    jrn_to_show = st.session_state['journal']
                else:
                    # display original one from db (must be edit mode)
                    jrn_to_show = jrn_sel
                    # display journal ID from DB:
                    st.markdown(f"Journal ID: :violet[**{jrn_sel['journal_id']}**] ")
                    
                # display journal and entries
                jrn_helper = JournalEntryHelper(jrn_to_show)
                
                st.caption('Debit Entries')
                debit_entries = st.data_editor(
                    data=jrn_helper.debit_entries,
                    num_rows='fixed',
                    use_container_width=True,
                    column_order=[
                        'acct_name',
                        'currency',
                        'amount',
                        'amount_base',
                        'description'
                    ],
                    column_config={
                        'acct_name': st.column_config.SelectboxColumn(
                            label='Account',
                            width=None,
                            options=dds_all_accts.options,
                            #required=True
                        ),
                        'currency': st.column_config.SelectboxColumn(
                            label='Currency',
                            width=None,
                            options=dds_currency.options,
                            #required=True
                        ),
                        'amount': st.column_config.NumberColumn(
                            label='Raw Amt',
                            width=None,
                            format='$ %.2f',
                            step=0.01,
                            #required=True
                        ),
                        'amount_base': st.column_config.NumberColumn(
                            label='Base Amt',
                            width=None,
                            format='$ %.2f',
                            step=0.01,
                            #required=True
                        ),
                        'description': st.column_config.TextColumn(
                            label='Description',
                            width=None,
                            #required=True,
                            default="" # need set this otherwise will be wrong dtype
                        ),
                    },
                    hide_index=True,
                    key='key_editor_debit',
                    disabled=True,
                )
                total_debit = sum(
                    e['amount_base'] 
                    for e in debit_entries
                    if pd.notnull(e['amount_base'])
                )
                st.markdown(f'📥 **Total Debit ({CurType(get_base_currency()).name})**: :green-background[{total_debit:.2f}]')
                
                st.caption('Credit Entries')
                credit_entries = st.data_editor(
                    #data=st.session_state.get('credit_entries', jhelper.credit_entries),
                    data=jrn_helper.credit_entries,
                    num_rows='fixed',
                    use_container_width=True,
                    column_order=[
                        'acct_name',
                        'currency',
                        'amount',
                        'amount_base',
                        'description'
                    ],
                    column_config={
                        'acct_name': st.column_config.SelectboxColumn(
                            label='Account',
                            width=None,
                            options=dds_all_accts.options,
                            #required=True
                        ),
                        'currency': st.column_config.SelectboxColumn(
                            label='Currency',
                            width=None,
                            options=dds_currency.options,
                            #required=True
                        ),
                        'amount': st.column_config.NumberColumn(
                            label='Raw Amt',
                            width=None,
                            format='$ %.2f',
                            step=0.01
                            #required=True
                        ),
                        'amount_base': st.column_config.NumberColumn(
                            label='Base Amt',
                            width=None,
                            format='$ %.2f',
                            step=0.01
                            #required=True
                        ),
                        'description': st.column_config.TextColumn(
                            label='Description',
                            width=None,
                            #required=True,
                            default="" # need set this otherwise will be wrong dtype
                        ),
                    },
                    hide_index=True,
                    key='key_editor_credit',
                    disabled=True
                )
                total_credit = sum(
                    e['amount_base'] 
                    for e in credit_entries
                    if pd.notnull(e['amount_base'])
                )
                st.markdown(f'📤 **Total Credit ({CurType(get_base_currency()).name})**: :blue-background[{total_credit:.2f}]')


        if edit_mode == 'Add' and st.session_state.get('validated', False):
            # add button
            st.button(
                label='Add Payment',
                on_click=add_purchase_payment,
                args=(payment_,)
            )
            
        elif edit_mode == 'Edit':
            btn_cols = st.columns([1, 1, 5])
            with btn_cols[1]:
                if st.session_state.get('validated', False):
                    # add invoice id to update
                    payment_.update({'payment_id': pmt_id_sel})
                    st.button(
                        label='Update',
                        type='secondary',
                        on_click=update_purchase_payment,
                        args=(payment_,)
                    )
            with btn_cols[0]:
                st.button(
                    label='Delete',
                    type='primary',
                    on_click=delete_purchase_payment,
                    kwargs=dict(
                        invoice_id=pmt_id_sel
                    )
                )
                
else:
    st.warning("No Customer found, must create supplier to add/edit payments", icon='🥵')