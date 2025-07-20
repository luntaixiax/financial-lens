import io
import math
import time
import uuid
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit.components.v1 as components
from datetime import datetime, date, timedelta
from utils.apis import get_file, list_property, get_account, get_property_journal, get_accounts_by_type, \
    validate_property, create_journal_from_new_property, get_all_accounts, get_base_currency, \
    add_property, update_property, delete_property, get_property_stat, get_comp_contact, get_logo
from utils.enums import PropertyType, PropertyTransactionType, CurType, AcctType, EntryType
from utils.tools import DropdownSelect, display_number
from utils.exceptions import NotExistError
from utils.apis import cookie_manager

st.set_page_config(layout="centered")
if cookie_manager.get("authenticated") != True:
    st.switch_page('sections/login.py')
access_token=cookie_manager.get("access_token")
base_cur = get_base_currency(access_token=access_token)

with st.sidebar:
    comp_name, _ = get_comp_contact(access_token=access_token)
    
    st.markdown(f"Hello, :rainbow[**{comp_name}**]")
    st.logo(get_logo(access_token=access_token), size='large')
    
    
def reset_validate():
    st.session_state['validated'] = False
    
def reset_page():
    reset_validate()

def clear_entries_from_cache():
    # st.session_state['validated'] = False
    pass
        
def clear_entries_and_reset_page():
    clear_entries_from_cache()
    reset_page()

def validate_property_(property_: dict):
    if property_['pur_dt'] is None:
        ui.alert_dialog(
            show=True, # TODO
            title="Purchase Date is missing",
            description='Must assign a purchase date',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return

    if property_['property_name'] in (None, ""):
        ui.alert_dialog(
            show=True, # TODO
            title="Property Name is missing",
            description='Must assign a property name',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    if property_['pur_acct_id'] in (None, ""):
        ui.alert_dialog(
            show=True, # TODO
            title="Purchase Account is missing",
            description='Must assign a purchase account',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    property_ = validate_property(property_, access_token=access_token)
    if isinstance(property_, dict):
        st.session_state['validated'] = True
        
        # calculate and journal to session state
        jrn_ = create_journal_from_new_property(property_, access_token=access_token)  
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
        
property_types = DropdownSelect.from_enum(
    PropertyType,
    include_null=False
)

properties = list_property(access_token=access_token)    

ast_accts = get_accounts_by_type(acct_type=AcctType.AST.value, access_token=access_token)
lib_accts = get_accounts_by_type(acct_type=AcctType.LIB.value, access_token=access_token)
equ_accts = get_accounts_by_type(acct_type=AcctType.EQU.value, access_token=access_token)

dds_balsh_accts = DropdownSelect(
    briefs=ast_accts + lib_accts + equ_accts,
    include_null=False,
    id_key='acct_id',
    display_keys=['acct_name']
)

all_accts = get_all_accounts(access_token=access_token)
dds_all_accts = DropdownSelect(
    briefs=all_accts,
    include_null=False,
    id_key='acct_id',
    display_keys=['acct_name']
)

dds_currency = DropdownSelect.from_enum(
    CurType,
    include_null=False
)

st.subheader("Properties (Fixed Asset)")
if len(properties) > 0:
    
    prop_stitch = []
    for p in properties:
        acct = get_account(p['pur_acct_id'], access_token=access_token)
        stat = get_property_stat(p['property_id'], rep_dt=datetime.now().date(), access_token=access_token)    
        prop = {
            #'Property ID': p['property_id'],
            'Property': p['property_name'],
            'Type': PropertyType(p['property_type']).name,
            'Purchase Date': p['pur_dt'],
            'Purchase Acct': acct['acct_name'],
            'Cost': f"{CurType(acct['currency']).name} {round(p['pur_cost'], 2):,.2f}",
            'Book Value': f"{CurType(acct['currency']).name} {round(stat['value'], 2):,.2f}",
        }
        prop_stitch.append(prop)
    
    property_display = pd.DataFrame.from_records(prop_stitch)

    ui.table(property_display)

else:
    st.info("No properties purchased yet!", icon='😐')
    
# if there is property, show the property details and show transactions

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
        index=0,
        horizontal=True,
        on_change=clear_entries_and_reset_page, # clear cache
        disabled=not(len(properties) > 0)
    )

if edit_mode == 'Edit':
    with widget_cols[1]:
        dds_property = DropdownSelect(
            briefs=properties,
            include_null=False,
            id_key='property_id',
            display_keys=['property_id', 'property_name']
        )
        edit_property = st.selectbox(
            label='👇 Select Property',
            options=dds_property.options,
            index=0
        )
        existing_property_id = dds_property.get_id(edit_property)
        existing_prop_item, jrn_sel = get_property_journal(existing_property_id, access_token=access_token)    
        
        if not 'journal' in st.session_state:
            st.session_state['journal'] = jrn_sel
        
st.divider()

if edit_mode == 'Edit':
    ui.badges(
        badge_list=[("Property ID", "default"), (existing_property_id, "secondary")], 
        class_name="flex gap-2", 
        key="badges1"
    )
    
prop_col1 = st.columns(2)
with prop_col1[0]:
    property_name = st.text_input(
        label="💻 Property Name",
        value="" if edit_mode == 'Add' else existing_prop_item['property_name'],
        type='default', 
        placeholder="property name here", 
        key="pname"
    )
    
with prop_col1[1]:
    if edit_mode == 'Add':
        
        property_type = st.radio(
            label = '🆎 Property Type',
            options=property_types.options,
            index=0,
            horizontal=True,
            key='radio1',
        )
    elif edit_mode == 'Edit':
        property_type = st.radio(
            label = '🆎 Property Type',
            options=property_types.options,
            index=property_types.get_idx_from_option(PropertyType(existing_prop_item['property_type']).name),
            horizontal=True,
            key='radio2',
        )

with prop_col1[0]:
    pur_date = st.date_input(
        label='📅 Purchase Date',
        value=date.today() if edit_mode == 'Add' else existing_prop_item['pur_dt'],
        key=f'date_input',
        disabled=False,
        on_change=reset_validate
    )

with prop_col1[1]:
    if edit_mode == 'Add':
        pur_acct = st.selectbox(
            label='💳 Purchase Account',
            options=dds_balsh_accts.options,
            key='acct_select',
            index=0,
            disabled=False,
            on_change=reset_validate
        )
    elif edit_mode == 'Edit':
        pur_acct = st.selectbox(
            label='💳 Purchase Account',
            options=dds_balsh_accts.options,
            key='acct_select2',
            index=dds_balsh_accts.get_idx_from_id(existing_prop_item['pur_acct_id']),
            disabled=False,
            on_change=reset_validate
        )
    
# get payment acct details
pur_acct_id = dds_balsh_accts.get_id(pur_acct)
pur_acct = get_account(pur_acct_id, access_token=access_token) 

with prop_col1[0]:
    pur_amt = st.number_input(
        label=f"💰 Purchase Price (Inclu. Tax) ({CurType(pur_acct['currency']).name})",
        value=0.0 if edit_mode == 'Add' else existing_prop_item['pur_price'],
        step=0.01,
        key='pur_amt',
        on_change=reset_validate
    )
    

with prop_col1[1]:
    pur_tax = st.number_input(
        label=f"🧾 Sales Tax ({CurType(pur_acct['currency']).name})",
        value=0.0 if edit_mode == 'Add' else existing_prop_item['tax'],
        step=0.01,
        key='tax',
        on_change=reset_validate
    )
    
note = st.text_input(
    label='📝 Note',
    value="" if edit_mode == 'Add' else existing_prop_item['note'],
    placeholder="property note here",
)

# add receipt section
receipt_section = st.container(border=True)
receipt_section.subheader("Manage receipts")
receipt_section.caption("Anything uploaded here, once click update/add, will append to existing receipts")
uploaded_files = receipt_section.file_uploader(
    "Upload Receipts", 
    accept_multiple_files=True,
    
)
files = []
for file in uploaded_files:
    # this must be BufferedReader to work properly
    bytes_file = io.BufferedReader(file)
    # this must be files to work properly
    files.append(('files', bytes_file))    

if edit_mode == 'Edit' and (recpt_ids := existing_prop_item['receipts']) is not None:
    receipts = []
    remove_receipts = []
    for recpt_id in recpt_ids:
        try:
            receipt = get_file(file_id = recpt_id, access_token=access_token)
        except NotExistError as e:
            receipt_section.error(f"{e.message}")
        else:
            receipts.append(receipt)

            # show receipts
            with receipt_section.expander(
                label = f"{receipt['filename']} | {receipt['file_id']}",
                expanded=False,
                icon='🖼️'
            ):
                try:
                    st.image(
                        image=receipt['content'],
                        caption=receipt['filehash']
                    )
                except Exception as e:
                    st.json({
                        'file_id': receipt['file_id'],
                        'file_hash': receipt['filehash']
                    })
                st.download_button(
                    label='Download Receipt',
                    data=receipt['content'],
                    file_name=receipt['filename'],
                    type='tertiary',
                    icon=":material/download:",
                )

# compile property object
property_ = {
    "property_name": property_name,
    "property_type": PropertyType[property_type].value,
    "pur_dt": pur_date.strftime('%Y-%m-%d'), # convert to string
    "pur_price": pur_amt,
    "tax": pur_tax,
    "pur_acct_id": pur_acct_id,
    "note": None if note == "" else note,
    "receipts": existing_prop_item['receipts'] if edit_mode == 'Edit' else None
}

validate_btn = st.button(
    label='Validate and Update Journal Entry Preview',
    on_click=validate_property_,
    args=(property_, )
)

# display journal entry
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
                    step=0.001,
                    #required=True
                ),
                'amount_base': st.column_config.NumberColumn(
                    label='Base Amt',
                    width=None,
                    format='$ %.2f',
                    step=0.001,
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
        st.markdown(f'📥 **Total Debit ({CurType(base_cur).name})**: :green-background[{display_number(total_debit)}]')  
        
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
                    step=0.001
                    #required=True
                ),
                'amount_base': st.column_config.NumberColumn(
                    label='Base Amt',
                    width=None,
                    format='$ %.2f',
                    step=0.001
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
        st.markdown(f'📤 **Total Credit ({CurType(base_cur).name})**: :blue-background[{display_number(total_credit)}]')  

if edit_mode == 'Add' and st.session_state.get('validated', False):
    # add button
    st.button(
        label='Add Property',
        on_click=add_property,
        args=(property_, files, access_token)
    )
    
elif edit_mode == 'Edit':
    btn_cols = st.columns([1, 1, 5])
    with btn_cols[1]:
        if st.session_state.get('validated', False):
            # add invoice id to update
            property_.update({'property_id': existing_property_id})
            st.button(
                label='Update',
                type='secondary',
                on_click=update_property,
                args=(property_, files, access_token)
            )
    with btn_cols[0]:
        st.button(
            label='Delete',
            type='primary',
            on_click=delete_property,
            kwargs=dict(
                property_id=existing_property_id,
                access_token=access_token
            )
        )
            
