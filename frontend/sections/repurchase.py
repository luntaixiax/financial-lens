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
from utils.apis import add_repur, create_journal_from_new_repur, delete_repur, get_account, get_accounts_by_type, get_all_accounts, get_base_currency, get_comp_contact, \
    get_repur_journal, get_logo, list_repur, update_repur, validate_repur
    
    
st.set_page_config(layout="centered")
with st.sidebar:
    comp_name, _ = get_comp_contact()
    
    st.markdown(f"Hello, :rainbow[**{comp_name}**]")
    st.logo(get_logo(), size='large')
    
def display_repur(repur: dict) -> dict:
    return {
        'repur_id': repur['repur_id'],
        'repur_dt': datetime.strptime(repur['repur_dt'], '%Y-%m-%d'),
        'num_shares': repur['num_shares'],
        'repur_price': repur['repur_price'],
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
    
def validate_repur_(repur_: dict):
    if repur_['repur_dt'] is None:
        ui.alert_dialog(
            show=True, # TODO
            title="Repurchase Date is missing",
            description='Must assign a repurchase date',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    if repur_['credit_acct_id'] in (None, ""):
        ui.alert_dialog(
            show=True, # TODO
            title="Payment Account is missing",
            description='Must assign a payment account',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    repur_ = validate_repur(repur_)
    if isinstance(repur_, dict):
        st.session_state['validated'] = True
        
        # calculate and journal to session state
        jrn_ = create_journal_from_new_repur(repur_)
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


ast_accts = get_accounts_by_type(acct_type=AcctType.AST.value)
lib_accts = get_accounts_by_type(acct_type=AcctType.LIB.value)
dds_pay_accts = DropdownSelect(
    briefs=ast_accts + lib_accts,
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
dds_currency = DropdownSelect.from_enum(
    CurType,
    include_null=False
)


base_cur_name = CurType(get_base_currency()).name

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
    
    repurs = list_repur()
    if len(repurs) > 0:
        repur_displays = map(display_repur, repurs)
        
        selected: dict = st.dataframe(
            data=repur_displays,
            use_container_width=True,
            hide_index=True,
            column_order=[
                #'repur_id',
                'repur_dt',
                'num_shares',
                'repur_price',
            ],
            column_config={
                'repur_dt': st.column_config.DateColumn(
                    label='Repurchase Date',
                    width=None,
                    pinned=True,
                ),
                'num_shares': st.column_config.NumberColumn(
                    label='# Shares',
                    width=None,
                    format='%.3f',
                    step=0.0001
                ),
                'repur_price': st.column_config.NumberColumn(
                    label=f'Repurchase Price ({base_cur_name})',
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
            rep_id_sel = repurs[_row_list[0]]['repur_id']
            repur_sel, jrn_sel = get_repur_journal(rep_id_sel)
            
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
        st.warning(f"No repurs found", icon='🥵')
        
        
# either add mode or selected edit/view mode
if edit_mode == 'Add' or (edit_mode == 'Edit' and len(repurs) > 0 and _row_list):

    
    reiss_cols = st.columns(2)
    with reiss_cols[0]:
        repur_dt = st.date_input(
            label='📅 Repurchase Date',
            value=date.today() if edit_mode == 'Add' else repur_sel['repur_dt'],
            key=f'date_input',
            disabled=False,
            on_change=reset_validate
        )
        
    iss_cols = st.columns(2)
    with iss_cols[0]:
        num_shares = st.number_input(
            label=f"#️⃣ # Shares",
            value=1.00 if edit_mode == 'Add' else repur_sel['num_shares'],
            key='num_shares',
            on_change=reset_validate
        )
        
    with iss_cols[1]:
        repur_price = st.number_input(
            label=f"🏷️ Repurchase Price ({base_cur_name})",
            value=0.01 if edit_mode == 'Add' else repur_sel['repur_price'],
            step=0.01,
            key='repur_price',
            on_change=reset_validate
        )
    
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
                index=dds_pay_accts.get_idx_from_id(repur_sel['credit_acct_id']),
                disabled=False,
                on_change=reset_validate
            )
            
        # get payment acct details
        pmt_acct_id = dds_pay_accts.get_id(pmt_acct)
        pmt_acct = get_account(pmt_acct_id)
        
    with iss_cols[1]:
        pmt_amt = st.number_input(
            label=f"💰 Payment Amount ({CurType(pmt_acct['currency'] or get_base_currency()).name})",
            value=0.0 if edit_mode == 'Add' else repur_sel['repur_amt'],
            step=0.01,
            key='pmt_amt',
            on_change=reset_validate
        )
        
    note = st.text_input(
        label='📝 Note',
        value="" if edit_mode == 'Add' else repur_sel['note'],
        placeholder="payment note here",
    )
    
    # compile repurs
    repur_ = {
        "repur_dt": repur_dt.strftime('%Y-%m-%d'), # convert to string
        "num_shares": num_shares,
        "repur_price": repur_price,
        "credit_acct_id": pmt_acct_id,
        "repur_amt": pmt_amt,
        "note": None if note == "" else note,
    }
    
    # TODO: only validate if in add mode or if in edit mode and actually changed something
    validate_btn = st.button(
        label='Validate and Update Journal Entry Preview',
        on_click=validate_repur_,
        args=(repur_, )
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
            st.markdown(f'📥 **Total Debit ({CurType(get_base_currency()).name})**: :green-background[{display_number(total_debit)}]')
            
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
            st.markdown(f'📤 **Total Credit ({CurType(get_base_currency()).name})**: :blue-background[{display_number(total_credit)}]')


    if edit_mode == 'Add' and st.session_state.get('validated', False):
        # add button
        st.button(
            label='Add Repurchase',
            on_click=add_repur,
            args=(repur_,)
        )
        
    elif edit_mode == 'Edit':
        btn_cols = st.columns([1, 1, 5])
        with btn_cols[1]:
            if st.session_state.get('validated', False):
                # add invoice id to update
                repur_.update({'repur_id': rep_id_sel})
                st.button(
                    label='Update',
                    type='secondary',
                    on_click=update_repur,
                    args=(repur_,)
                )
        with btn_cols[0]:
            st.button(
                label='Delete',
                type='primary',
                on_click=delete_repur,
                kwargs=dict(
                    repur_id=rep_id_sel
                )
            )