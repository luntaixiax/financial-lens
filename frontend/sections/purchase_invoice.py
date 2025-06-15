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
from utils.apis import get_fx, list_supplier, list_item, list_purchase_invoice, get_purchase_invoice_journal, \
    get_item, get_default_tax_rate, get_accounts_by_type, validate_purchase, \
    create_journal_from_new_purchase_invoice, get_all_accounts, add_purchase_invoice, \
    update_purchase_invoice, delete_purchase_invoice, get_base_currency, preview_purchase_invoice, \
    get_comp_contact, get_logo

st.set_page_config(layout="wide")
with st.sidebar:
    comp_name, _ = get_comp_contact()
    
    st.markdown(f"Hello, :rainbow[**{comp_name}**]")
    st.logo(get_logo(), size='large')
    
    
def display_invoice(invoice: dict) -> dict:
    return {
        'invoice_id': invoice['invoice_id'],
        'invoice_num': invoice['invoice_num'],
        'invoice_dt': datetime.strptime(invoice['invoice_dt'], '%Y-%m-%d'),
        'entity_name': invoice['entity_name'],
        'subject': invoice['subject'],
        'currency': CurType(invoice['currency']).name,
        'num_invoice_items': invoice['num_invoice_items'],
        'total_raw_amount': invoice['total_raw_amount'],
        'total_base_amount': invoice['total_base_amount'],
    }
    
def display_item(item: dict) -> dict:
    # convert enums
    r = {}
    r['item_id'] = item['item_id']
    r['name'] = item['name']
    r['item_type'] = ItemType(item['item_type']).name
    r['unit'] = UnitType(item['unit']).name
    r['currency'] = CurType(item['currency']).name
    r['unit_price'] = item['unit_price']
    return r

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

def reset_validate():
    st.session_state['validated'] = False
    
def reset_page():
    reset_validate()
    if 'journal' in st.session_state:
        del st.session_state['journal']

def clear_entries_from_cache():
    # st.session_state['validated'] = False
    
    if 'invoice_item_entries' in st.session_state:
        del st.session_state['invoice_item_entries']
    if 'general_invoice_item_entries' in st.session_state:
        del st.session_state['general_invoice_item_entries']
    if 'subtotal_invitems' in st.session_state:
        del st.session_state['subtotal_invitems']
    if 'subtotal_ginvitems' in st.session_state:
        del st.session_state['subtotal_ginvitems']
    if 'subtotal' in st.session_state:
        del st.session_state['subtotal']
    if 'tax_amount' in st.session_state:
        del st.session_state['tax_amount']
    if 'total' in st.session_state:
        del st.session_state['total']
    if 'journal' in st.session_state:
        del st.session_state['journal']

def clear_entries_and_reset_page():
    clear_entries_from_cache()
    reset_page()

def update_inv_item(entry: dict) -> dict:
    if entry.get('item_id') is not None:
        item = get_item(dds_citems.get_id(entry['item_id']))
        entry['unit_price'] = item['unit_price']
    else:
        entry['unit_price'] = None
    
    if (
        (unit_pirce := entry.get('unit_price')) is not None
        and (quantity := entry.get('quantity')) is not None
        and (discount_rate := entry.get('discount_rate')) is not None
    ):
        entry['amount_pre_tax'] = unit_pirce * quantity * (1 - discount_rate / 100)
        
    # set default account to record this
    entry['acct_name'] = dds_exp_accts._mappings.get(item['default_acct_id'])
        
    return entry

def on_change_inv_items():
    # whenever edited the table
    reset_validate()
    st.session_state['subtotal_invitems'] = '-'
    st.session_state['subtotal'] = '-'
    st.session_state['tax_amount'] = '-'
    st.session_state['total'] = '-'
    
    
    # get changes from data editor
    state = st.session_state['key_editor_inv_items']
    
    # edit
    for index, updates in state["edited_rows"].items():
        st.session_state['invoice_item_entries'][index].update(updates)
    # add new row
    for new_row in state["added_rows"]:
        st.session_state['invoice_item_entries'].append(new_row)
    # delete row TODO: which comes first, add or delete
    for idx in sorted(state["deleted_rows"], reverse=True):
        # need to reversly delete, bc delete on update will get out of range error
        st.session_state['invoice_item_entries'].pop(idx)
        
    for i, e in enumerate(st.session_state['invoice_item_entries']):
        new_e = update_inv_item(e)
        # edit
        for k, v in new_e.items():
            st.session_state['invoice_item_entries'][i][k] = v

def update_general_inv_item(entry: dict) -> dict:
    if (incur_date := entry.get('incur_dt')) is not None:
        if isinstance(incur_date, str):
            entry['incur_dt'] = datetime.strptime(incur_date, '%Y-%m-%d')#.date()
    
    if (
        (amount_pre_tax_raw := entry.get('amount_pre_tax_raw')) is not None
        and (currency := entry.get('currency')) is not None
        and (incur_date := entry.get('incur_dt')) is not None
        and (amount_pre_tax := entry.get('amount_pre_tax') is None) # only if amount billed not filled
    ):
        entry['amount_pre_tax'] = amount_pre_tax_raw * get_fx(
            src_currency=CurType[currency].value,
            tgt_currency=CurType[inv_cur_type_option].value,
            cur_dt=entry.get('incur_dt').date()
        )
        
    return entry

def on_change_general_inv_items():
    # whenever edited the table
    reset_validate()
    st.session_state['subtotal_ginvitems'] = '-'
    st.session_state['subtotal'] = '-'
    st.session_state['tax_amount'] = '-'
    st.session_state['total'] = '-'
    # get changes from data editor
    state = st.session_state['key_editor_general_inv_items']
    
    # edit
    for index, updates in state["edited_rows"].items():
        st.session_state['general_invoice_item_entries'][index].update(updates)
    # add new row
    for new_row in state["added_rows"]:
        st.session_state['general_invoice_item_entries'].append(new_row)
    # delete row TODO: which comes first, add or delete
    for idx in sorted(state["deleted_rows"], reverse=True):
        # need to reversly delete, bc delete on update will get out of range error
        st.session_state['general_invoice_item_entries'].pop(idx)
        
    for i, e in enumerate(st.session_state['general_invoice_item_entries']):
        new_e = update_general_inv_item(e)
        # edit
        for k, v in new_e.items():
            st.session_state['general_invoice_item_entries'][i][k] = v

        
def convert_inv_items_to_db(inv_item_entries: list[dict]) -> list[dict]:
    items = []
    for e in inv_item_entries:
        # check if required items all available
        if e.get('item_id') is None:
            continue
        if e.get('acct_name') is None:
            continue
        if e.get('quantity') is None:
            continue
        if e.get('tax_rate') is None:
            continue
        if e.get('discount_rate') is None:
            continue
        
        r = {}
        r['item'] = get_item(dds_citems.get_id(e['item_id']))
        r['quantity'] = e['quantity']
        r['acct_id'] = dds_exp_accts.get_id(e['acct_name'])
        r['tax_rate'] = e['tax_rate'] / 100
        r['discount_rate'] = e['discount_rate'] / 100
        r['description'] = e['description']
        
        items.append(r)
    return items

def convert_general_inv_items_to_db(general_inv_item_entries: list[dict]) -> list[dict]:
    items = []
    for e in general_inv_item_entries:
        # check if required items all available
        if e.get('incur_dt') is None:
            continue
        if e.get('acct_name') is None:
            continue
        if e.get('currency') is None:
            continue
        if e.get('amount_pre_tax_raw') is None:
            continue
        if e.get('amount_pre_tax') is None:
            continue
        if e.get('tax_rate') is None:
            continue
        
        r = {}
        r['incur_dt'] = e['incur_dt'].strftime('%Y-%m-%d')
        r['acct_id'] = dds_incexp_accts.get_id(e['acct_name'])
        r['currency'] = CurType[e['currency']].value
        r['amount_pre_tax_raw'] = e['amount_pre_tax_raw']
        r['amount_pre_tax'] = e['amount_pre_tax']
        r['tax_rate'] = e['tax_rate'] / 100
        r['description'] = e['description']
        
        items.append(r)
    return items

def validate_invoice(invoice_: dict):
    # TODO: get back validated invoice with computed field and write to st.session_state for display
    # at least have 1 item
    if len(invoice_['invoice_items']) + len(invoice_['ginvoice_items']) < 1:
        ui.alert_dialog(
            show=True, # TODO
            title="At least have one predefined invoice item or general invoice item",
            description='Have no items defined',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    # detect if payment key info is missing
    if invoice_['invoice_num'] in (None, ""):
        ui.alert_dialog(
            show=True, # TODO
            title="Invoice Number is missing",
            description='Must assign a invoice number',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    if invoice_['subject'] in (None, ""):
        ui.alert_dialog(
            show=True, # TODO
            title="Subject is missing",
            description='Must assign a subject',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    invoice_ = validate_purchase(invoice_)
    if isinstance(invoice_, dict):
        if invoice_.get('subtotal_invitems') is not None:
            # pass the validation, otherwise may not pass, just pop up alerts
            st.session_state['subtotal_invitems'] = invoice_['subtotal_invitems']
            st.session_state['subtotal_ginvitems'] = invoice_['subtotal_ginvitems']
            st.session_state['subtotal'] = invoice_['subtotal']
            st.session_state['tax_amount'] = invoice_['tax_amount']
            st.session_state['total'] = invoice_['total']
            st.session_state['validated'] = True

            # calculate and journal to session state
            jrn_ = create_journal_from_new_purchase_invoice(invoice_)
            st.session_state['journal'] = jrn_
            
            return
            
    ui.alert_dialog(
        show=True, # TODO
        title="Unknown Error, can not be validated",
        description="",
        confirm_label="OK",
        cancel_label="Cancel",
        key=str(uuid.uuid1())
    )
    

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
    inc_accts = get_accounts_by_type(acct_type=AcctType.INC.value)
    exp_accts = get_accounts_by_type(acct_type=AcctType.EXP.value)
    dds_exp_accts = DropdownSelect(
        briefs=exp_accts,
        include_null=False,
        id_key='acct_id',
        display_keys=['acct_name']
    )
    dds_incexp_accts = DropdownSelect(
        briefs=inc_accts + exp_accts,
        include_null=False,
        id_key='acct_id',
        display_keys=['acct_name']
    )
    all_accts = get_all_accounts()
    dds_accts = DropdownSelect(
        briefs=all_accts,
        include_null=False,
        id_key='acct_id',
        display_keys=['acct_name']
    )

    widget_cols = st.columns([1, 4])
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
            on_change=clear_entries_and_reset_page, # clear cache
        )

    with widget_cols[1]:
        edit_supplier = st.selectbox(
            label='👇 Select Customer',
            options=dds_suppliers.options,
            index=0
        )
        supplier_id = dds_suppliers.get_id(edit_supplier)
        
    # either add mode or selected edit/view mode
    if edit_mode == 'Edit':
        
        invoices = list_purchase_invoice(supplier_ids=[supplier_id])
        
        inv_displays = map(display_invoice, invoices)
        selected: dict = st.dataframe(
            data=inv_displays,
            use_container_width=True,
            hide_index=True,
            column_order=[
                'invoice_num',
                'invoice_dt',
                #'entity_name',
                'subject',
                'currency',
                'num_invoice_items',
                'total_raw_amount',
                'total_base_amount'
            ],
            column_config={
                'invoice_num': st.column_config.TextColumn(
                    label='Invoice Num',
                    width=None,
                    pinned=True
                ),
                'invoice_dt': st.column_config.DateColumn(
                    label='Date',
                    width=None,
                    pinned=True,
                ),
                'subject': st.column_config.TextColumn(
                    label='Subject',
                    width=None,
                    pinned=True,
                ),
                'currency': st.column_config.SelectboxColumn(
                    label='Currency',
                    width=None,
                    options=dds_currency.options,
                    #required=True
                ),
                'num_invoice_items': st.column_config.NumberColumn(
                    label='# Items',
                    width=None,
                    format='%d'
                ),
                'total_raw_amount': st.column_config.NumberColumn(
                    label='$Raw Amount',
                    width=None,
                    format='$ %.2f'
                ),
                'total_base_amount': st.column_config.NumberColumn(
                    label='$Base Amount',
                    width=None,
                    format='$ %.2f'
                ),
            },
            on_select=clear_entries_from_cache,
            selection_mode=(
                'single-row',
            )
        )

        st.divider()

        if  _row_list := selected['selection']['rows']:
            inv_id_sel = invoices[_row_list[0]]['invoice_id']
            inv_sel, jrn_sel = get_purchase_invoice_journal(inv_id_sel)

            ui.badges(
                badge_list=[("Invoice ID", "default"), (inv_id_sel, "secondary")], 
                class_name="flex gap-2", 
                key="badges1"
            )
            
    # either add mode or selected edit/view mode
    if edit_mode == 'Add' or (edit_mode == 'Edit' and _row_list):
        
        inv_cols = st.columns(2)
        with inv_cols[0]:
            inv_num = st.text_input(
                label='#️⃣ Invoice Number',
                value="" if edit_mode == 'Add' else inv_sel['invoice_num'],
                type='default', 
                placeholder="invoice number here", 
            )
            inv_date = st.date_input(
                label='📅 Invoice Date',
                value=date.today() if edit_mode == 'Add' else inv_sel['invoice_dt'],
                key=f'date_input',
                disabled=False,
                on_change=reset_validate
            )
            inv_cur_type_option = st.selectbox(
                label='💲 Currency',
                options=dds_currency.options,
                key='cur_type_select',
                index=0 if edit_mode == 'Add' else dds_currency.get_idx_from_id(CurType(inv_sel['currency']).value),
                disabled=(edit_mode == 'Edit'), # avoid error, changing currency means items all become invalid,
                on_change=reset_validate
            )
            inv_cur = CurType[inv_cur_type_option].name
            
            
        with inv_cols[1]:
            inv_subject = st.text_input(
                label='📕 Subject',
                value="" if edit_mode == 'Add' else inv_sel['subject'],
                type='default', 
                placeholder="invoice subject here", 
            )
            inv_due_date = st.date_input(
                label='⏰ Due Date',
                value=date.today() + timedelta(days=5) if edit_mode == 'Add' else inv_sel['due_dt'],
                key=f'due_date_input',
                disabled=False
            )
            inv_shipping = st.number_input(
                label='🚚 Shipping Charge',
                value=0.0 if edit_mode == 'Add' else inv_sel['shipping'],
                step=0.01,
                key='ship_charge_num',
                on_change=reset_validate
            )
        
        inv_note = st.text_input(
            label='📝 Note',
            value="" if edit_mode == 'Add' else inv_sel['note'],
            type='default', 
            placeholder="invoice note here", 
        )
        
        # get item list (filter by currency)
        items = list_item(entity_type=EntityType.SUPPLIER.value)
        items = list(map(
            display_item, filter(
                lambda e: e['currency'] == CurType[inv_cur_type_option].value, 
                items
            )
        ))
        dds_citems = DropdownSelect(
            briefs=items,
            include_null=False,
            id_key='item_id',
            display_keys=['name', 'unit_price']
        )
        
        # prepare data editor
        if edit_mode == 'Edit':
            invoice_items = [
                {
                    'item_id': dds_citems._mappings.get(it['item']['item_id']),
                    'unit_price': it['item']['unit_price'],
                    'quantity': it['quantity'],
                    'tax_rate': it['tax_rate'] * 100,
                    'discount_rate': it['discount_rate'] * 100,
                    'amount_pre_tax': it['amount_pre_tax'],
                    'acct_name': dds_exp_accts._mappings.get(it['acct_id']),
                    'description': it['description'],
                } for it in inv_sel['invoice_items']
            ]
            general_invoice_items = [
                {
                    'incur_dt': datetime.strptime(git['incur_dt'], '%Y-%m-%d'),
                    'acct_name': dds_incexp_accts._mappings.get(git['acct_id']),
                    'currency': CurType(git['currency']).name, # TODO
                    'amount_pre_tax_raw': git['amount_pre_tax_raw'],
                    'amount_pre_tax': git['amount_pre_tax'],
                    'tax_rate': git['tax_rate'] * 100,
                    'description': git['description'],
                } for git in inv_sel['ginvoice_items']
            ]
            # a bug that if existing invoice does not have general term, UI will not allow add new line
            if len(general_invoice_items) == 0:
                general_invoice_items = [{c: None for c in [
                    'incur_dt',
                    'acct_name',
                    'currency',
                    'amount_pre_tax_raw',
                    'amount_pre_tax',
                    'tax_rate',
                    'description'
                ]}]
            
            
            if not 'subtotal_invitems' in st.session_state:
                st.session_state['subtotal_invitems'] = inv_sel['subtotal_invitems']
            if not 'subtotal_ginvitems' in st.session_state:
                st.session_state['subtotal_ginvitems'] = inv_sel['subtotal_ginvitems']
            if not 'subtotal' in st.session_state:
                st.session_state['subtotal'] = inv_sel['subtotal']
            if not 'tax_amount' in st.session_state:
                st.session_state['tax_amount'] = inv_sel['tax_amount']
            if not 'total' in st.session_state:
                st.session_state['total'] = inv_sel['total']
                
            if not 'journal' in st.session_state:
                st.session_state['journal'] = jrn_sel
        else:
            invoice_items = [{c: None for c in [
                'item_id',
                'unit_price',
                'quantity',
                'tax_rate',
                'discount_rate',
                'amount_pre_tax',
                'acct_name',
                'description'
            ]}]
            invoice_items[0]['discount_rate'] = 0
            invoice_items[0]['tax_rate'] = get_default_tax_rate() * 100
            
            general_invoice_items = [{c: None for c in [
                'incur_dt',
                'acct_name',
                'currency',
                'amount_pre_tax_raw',
                'amount_pre_tax',
                'tax_rate',
                'description'
            ]}]
            
        if 'invoice_item_entries' not in st.session_state:
            st.session_state['invoice_item_entries'] = invoice_items
        if 'general_invoice_item_entries' not in st.session_state:
            st.session_state['general_invoice_item_entries'] = general_invoice_items
        
        # invoice items
        inv_item_container = st.container(border=True)
        inv_item_container.subheader('Invoice Items')
        inv_item_container.caption('put predefined invoice items here')
        inv_item_entries = inv_item_container.data_editor(
            data=st.session_state['invoice_item_entries'],
            #data=st.session_state['debit_entries'],
            num_rows='dynamic',
            use_container_width=True,
            column_order=[
                'item_id',
                'unit_price',
                'quantity',
                'discount_rate',
                'amount_pre_tax',
                'tax_rate',
                'acct_name',
                'description'
            ],
            column_config={
                'item_id': st.column_config.SelectboxColumn(
                    label='Item',
                    width=None,
                    options=dds_citems.options,
                    #required=True
                ),
                'unit_price': st.column_config.NumberColumn(
                    label='Unit Price',
                    width=None,
                    format='$ %.3f',
                    step=0.001,
                    disabled=True
                    #required=True
                ),
                'quantity': st.column_config.NumberColumn(
                    label='Quantity',
                    width=None,
                    format='%.6f',
                    step=0.000001,
                    #required=True
                ),
                'tax_rate': st.column_config.NumberColumn(
                    label='Tax Rate',
                    width=None,
                    format='%.2f%%',
                    step=0.01,
                    min_value=0.0,
                    max_value=100.0,
                    default=get_default_tax_rate() * 100,
                    #required=True
                ),
                'discount_rate': st.column_config.NumberColumn(
                    label='Discount Rate',
                    width=None,
                    format='%.2f%%',
                    step=0.01,
                    min_value=0.0,
                    max_value=100.0,
                    default=0
                    #required=True
                ),
                'amount_pre_tax': st.column_config.NumberColumn(
                    label='Pre Tax',
                    width=None,
                    format='$ %.2f',
                    step=0.01,
                    disabled=True
                    #required=True
                ),
                'acct_name': st.column_config.SelectboxColumn(
                    label='Income Acct',
                    width=None,
                    options=dds_exp_accts.options,
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
            key='key_editor_inv_items',
            disabled=False,
            on_change=on_change_inv_items,
        )
        
        total_inv_items = st.session_state.get('subtotal_invitems', '-')
        inv_item_container.markdown(f"📐 **Total Invoice Items {inv_cur}**: {total_inv_items if total_inv_items != '-' else '-'}")
        
        # general invoice items
        general_inv_item_container = st.container(border=True)
        general_inv_item_container.subheader('General Items')
        general_inv_item_container.caption('for example, put billable expense here')
        general_inv_item_entries = general_inv_item_container.data_editor(
            data=st.session_state['general_invoice_item_entries'],
            #data=st.session_state['debit_entries'],
            num_rows='dynamic',
            use_container_width=True,
            column_order=[
                'incur_dt',
                'acct_name',
                'currency',
                'amount_pre_tax_raw',
                'amount_pre_tax',
                'tax_rate',
                'description'
            ],
            column_config={
                'incur_dt': st.column_config.DateColumn(
                    label='Incur Date',
                    width=None,
                    default=datetime.today(), 
                    #required=True
                ),
                'acct_name': st.column_config.SelectboxColumn(
                    label='Bill Acct',
                    width=None,
                    options=dds_incexp_accts.options,
                    #required=True
                ),
                'currency': st.column_config.SelectboxColumn(
                    label='Currency',
                    width=None,
                    options=dds_currency.options,
                    #required=True
                ),
                'amount_pre_tax_raw': st.column_config.NumberColumn(
                    label='Raw Amount',
                    width=None,
                    format='$ %.2f',
                    step=0.01,
                    #required=True
                ),
                'amount_pre_tax': st.column_config.NumberColumn(
                    label=f'Invoice Amount ({inv_cur})',
                    width=None,
                    format='$ %.2f',
                    step=0.01,
                    #required=True
                ),
                'tax_rate': st.column_config.NumberColumn(
                    label='Tax Rate',
                    width=None,
                    format='%.2f%%',
                    step=0.01,
                    min_value=0.0,
                    max_value=100.0,
                    default=get_default_tax_rate() * 100,
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
            key='key_editor_general_inv_items',
            disabled=False,
            on_change=on_change_general_inv_items,
        )
        total_ginvitems = st.session_state.get('subtotal_ginvitems', '-')
        general_inv_item_container.markdown(f"🍥 **Total General Items {inv_cur}**: {total_ginvitems if total_ginvitems != '-' else '-'}")
        
        # total amount and tax
        subtotal = st.session_state.get('subtotal', '-')
        st.markdown(f"🛒 **SubTotal {inv_cur}**: {subtotal if subtotal != '-' else '-'}")
        
        tax_amount = st.session_state.get('tax_amount', '-')
        st.markdown(f"🧾 **Tax Amount {inv_cur}**: {tax_amount if tax_amount != '-' else '-'}")
        
        total = st.session_state.get('total', '-')
        st.markdown(f"💵 **Total {inv_cur}**: {total if total != '-' else '-'}")
        
        invoice_ = {
            #"invoice_id": "string",
            "entity_type": 2, # supplier
            "entity_id": supplier_id,
            "invoice_num": inv_num,
            "invoice_dt": inv_date.strftime('%Y-%m-%d'), # convert to string
            "due_dt": inv_due_date.strftime('%Y-%m-%d'),
            "subject": inv_subject,
            "currency": CurType[inv_cur_type_option].value,
            "invoice_items": convert_inv_items_to_db(inv_item_entries),
            "ginvoice_items": convert_general_inv_items_to_db(general_inv_item_entries),
            "shipping": inv_shipping,
            "note": inv_note
        }
        
        # TODO: only validate if in add mode or if in edit mode and actually changed something
        validate_btn = st.button(
            label='Validate and Update Journal Entry Preview',
            on_click=validate_invoice,
            args=(invoice_, )
        )
        
        
        if (edit_mode == 'Add' and st.session_state.get('validated', False)) or edit_mode == 'Edit':
            # display only in 2 scenarios:
            # 1. if add mode, but be validated (otherwise will be void)
            # 2. if edit mode, must display whether been updated or not
            with st.expander(label='Journal Entries', expanded=True, icon='📔'):
                #jrn_container = st.container(border=True)
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
                            options=dds_accts.options,
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
                            options=dds_accts.options,
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
                label='Add Invoice',
                on_click=add_purchase_invoice,
                args=(invoice_,)
            )
            
        elif edit_mode == 'Edit':
            btn_cols = st.columns([1, 1, 5])
            with btn_cols[1]:
                if st.session_state.get('validated', False):
                    # add invoice id to update
                    invoice_.update({'invoice_id': inv_id_sel})
                    st.button(
                        label='Update',
                        type='secondary',
                        on_click=update_purchase_invoice,
                        args=(invoice_,)
                    )
            with btn_cols[0]:
                st.button(
                    label='Delete',
                    type='primary',
                    on_click=delete_purchase_invoice,
                    kwargs=dict(
                        invoice_id=inv_id_sel
                    )
                )
                
        if edit_mode == 'Edit':
            with st.container(border=True):
                st.subheader("Invoice Preview")
                # show purchase invoice HTML preview
                components.iframe(
                    f"data:text/html;base64,{preview_purchase_invoice(inv_id_sel)}",
                    height = 1250, 
                    scrolling=True
                )
                
else:
    st.warning("No Customer found, must create supplier to add/edit purchase", icon='🥵')