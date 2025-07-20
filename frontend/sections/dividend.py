import math
import time
import io
import uuid
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import streamlit as st
import streamlit_shadcn_ui as ui
from datetime import datetime, date
from utils.tools import DropdownSelect, display_number
from utils.exceptions import NotExistError
from utils.enums import AcctType, CurType, EntryType, JournalSrc
from utils.apis import add_div, create_journal_from_new_div, delete_div, \
    get_account, get_accounts_by_type, get_all_accounts, get_base_currency, get_comp_contact, \
    get_div_journal, get_logo, list_div, update_div, validate_div
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
    
def display_div(div: dict) -> dict:
    acct = get_account(div['credit_acct_id'], access_token=access_token)
    return {
        'div_id': div['div_id'],
        'div_dt': datetime.strptime(div['div_dt'], '%Y-%m-%d'),
        'payment_acct': acct['acct_name'],
        'currency': CurType(acct['currency']).name,
        'div_amt': div['div_amt']
    }
    
def clear_entries_from_cache(): 
    pass

def reset_validate():
    st.session_state['validated'] = False
    
def reset_page():
    reset_validate()
    
def clear_entries_and_reset_page():
    clear_entries_from_cache()
    reset_page()
    
def validate_div_(div_: dict):
    if div_['div_dt'] is None:
        ui.alert_dialog(
            show=True, # TODO
            title="Dividend Date is missing",
            description='Must assign a divchase date',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    if div_['credit_acct_id'] in (None, ""):
        ui.alert_dialog(
            show=True, # TODO
            title="Payment Account is missing",
            description='Must assign a payment account',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    div_ = validate_div(div_, access_token=access_token)
    if isinstance(div_, dict):
        st.session_state['validated'] = True
        
        # calculate and journal to session state
        jrn_ = create_journal_from_new_div(div_, access_token=access_token)
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


ast_accts = get_accounts_by_type(acct_type=AcctType.AST.value, access_token=access_token)
lib_accts = get_accounts_by_type(acct_type=AcctType.LIB.value, access_token=access_token)
dds_pay_accts = DropdownSelect(
    briefs=ast_accts + lib_accts,
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


base_cur_name = CurType(get_base_currency(access_token=access_token)).name

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
if edit_mode == 'Edit':
    
    divs = list_div(access_token=access_token)
    if len(divs) > 0:
        div_displays = map(display_div, divs)
        
        selected: dict = st.dataframe(
            data=div_displays,
            use_container_width=True,
            hide_index=True,
            column_order=[
                #'div_id',
                'div_dt',
                'payment_acct',
                'currency',
                'div_amt',
            ],
            column_config={
                'div_dt': st.column_config.DateColumn(
                    label='Dividend Date',
                    width=None,
                    pinned=True,
                ),
                'payment_acct': st.column_config.SelectboxColumn(
                    label='Account',
                    width=None,
                    options=dds_pay_accts.options,
                    #required=True
                ),
                'currency': st.column_config.SelectboxColumn(
                    label='Currency',
                    width=None,
                    options=dds_currency.options,
                    #required=True
                ),
                'div_amt': st.column_config.NumberColumn(
                    label=f'Dividend Amount',
                    width=None,
                    format='$ %.2f',
                    step=0.001
                ),

            },
            on_select=clear_entries_from_cache,
            selection_mode=(
                'single-row',
            )
        )
        
        
        st.divider()

        if  _row_list := selected['selection']['rows']:
            rep_id_sel = divs[_row_list[0]]['div_id']
            div_sel, jrn_sel = get_div_journal(rep_id_sel, access_token=access_token)  
            
            badge_cols = st.columns([1, 2])
            with badge_cols[0]:
                ui.badges(
                    badge_list=[("Issue ID", "default"), (rep_id_sel, "secondary")], 
                    class_name="flex gap-2", 
                    key="badges1"
                )
            with badge_cols[1]:
                ui.badges(
                    badge_list=[("Journal ID", "destructive"), (jrn_sel['journal_id'], "secondary")], 
                    class_name="flex gap-2", 
                    key="badges2"
                )
        
    else:
        st.warning(f"No divs found", icon='🥵')
        
        
# either add mode or selected edit/view mode
if edit_mode == 'Add' or (edit_mode == 'Edit' and len(divs) > 0 and _row_list):

    
    reiss_cols = st.columns(2)
    with reiss_cols[0]:
        div_dt = st.date_input(
            label='📅 Dividend Date',
            value=date.today() if edit_mode == 'Add' else div_sel['div_dt'],
            key=f'date_input',
            disabled=False,
            on_change=reset_validate
        )
        
    iss_cols = st.columns(2)
    
    with iss_cols[0]:
        if edit_mode == 'Add':
            pmt_acct = st.selectbox(
                label='💳 Payment Account',
                options=dds_pay_accts.options,
                key='acct_select',
                index=0,
                disabled=False,
                on_change=reset_validate
            )
        elif edit_mode == 'Edit':
            pmt_acct = st.selectbox(
                label='💳 Payment Account',
                options=dds_pay_accts.options,
                key='acct_select2',
                index=dds_pay_accts.get_idx_from_id(div_sel['credit_acct_id']),
                disabled=False,
                on_change=reset_validate
            )
            
        # get payment acct details
        pmt_acct_id = dds_pay_accts.get_id(pmt_acct)
        pmt_acct = get_account(pmt_acct_id, access_token=access_token)
        
    with iss_cols[1]:
        pmt_amt = st.number_input(
            label=f"💰 Payment Amount ({CurType(pmt_acct['currency'] or base_cur).name})",       
            value=0.0 if edit_mode == 'Add' else div_sel['div_amt'],
            step=0.01,
            key='pmt_amt',
            on_change=reset_validate
        )
        
    note = st.text_input(
        label='📝 Note',
        value="" if edit_mode == 'Add' else div_sel['note'],
        placeholder="payment note here",
    )
    
    # compile divs
    div_ = {
        "div_dt": div_dt.strftime('%Y-%m-%d'), # convert to string
        "credit_acct_id": pmt_acct_id,
        "div_amt": pmt_amt,
        "note": None if note == "" else note,
    }
    
    # TODO: only validate if in add mode or if in edit mode and actually changed something
    validate_btn = st.button(
        label='Validate and Update Journal Entry Preview',
        on_click=validate_div_,
        args=(div_, )
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
            label='Add Dividend',
            on_click=add_div,
            args=(div_, access_token)
        )
        
    elif edit_mode == 'Edit':
        btn_cols = st.columns([1, 1, 5])
        with btn_cols[1]:
            if st.session_state.get('validated', False):
                # add invoice id to update
                div_.update({'div_id': rep_id_sel})
                st.button(
                    label='Update',
                    type='secondary',
                    on_click=update_div,
                    args=(div_, access_token)
                )
        with btn_cols[0]:
            st.button(
                label='Delete',
                type='primary',
                on_click=delete_div,
                kwargs=dict(
                    div_id=rep_id_sel,
                    access_token=access_token
                )
            )