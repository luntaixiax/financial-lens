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
from utils.apis import add_issue, create_journal_from_new_issue, delete_issue, get_account, get_accounts_by_type, \
    get_all_accounts, get_base_currency, get_comp_contact, get_issue_journal, get_logo, list_issue, \
    list_repur, get_total_reissue_from_repur, update_issue, validate_issue
from utils.apis import cookie_manager

st.set_page_config(layout="centered")
if cookie_manager.get("authenticated") != True:
    st.switch_page('sections/login.py')
access_token=cookie_manager.get("access_token")

with st.sidebar:
    comp_name, _ = get_comp_contact(access_token=access_token)
    
    st.markdown(f"Hello, :rainbow[**{comp_name}**]")
    st.logo(get_logo(access_token=access_token), size='large')
    
def display_issue(issue: dict) -> dict:
    return {
        'issue_id': issue['issue_id'],
        'issue_dt': datetime.strptime(issue['issue_dt'], '%Y-%m-%d'),
        'is_reissue': issue['is_reissue'],
        'num_shares': issue['num_shares'],
        'issue_price': issue['issue_price'],
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
    
def validate_issue_(issue_: dict):
    if issue_['issue_dt'] is None:
        ui.alert_dialog(
            show=True, # TODO
            title="Issue Date is missing",
            description='Must assign a issue date',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    if issue_['debit_acct_id'] in (None, ""):
        ui.alert_dialog(
            show=True, # TODO
            title="Payment Account is missing",
            description='Must assign a payment account',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    issue_ = validate_issue(issue_)
    if isinstance(issue_, dict):
        st.session_state['validated'] = True
        
        # calculate and journal to session state
        jrn_ = create_journal_from_new_issue(issue_)
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
exp_accts = get_accounts_by_type(acct_type=AcctType.EXP.value, access_token=access_token)
dds_pay_accts = DropdownSelect(
    briefs=ast_accts + lib_accts + exp_accts,
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
repurs = list_repur(access_token=access_token)
dds_repurs = DropdownSelect(
    briefs=repurs,
    include_null=False,
    id_key='repur_id',
    display_keys=['repur_dt', 'num_shares', 'repur_price']
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
    
    reissues = list_issue(is_reissue=True)
    issues = list_issue(is_reissue=False)
    issues = sorted(issues + reissues, key=lambda i: i['issue_dt'])
    
    if len(issues) > 0:
        
        issue_displays = map(display_issue, issues)
        
        selected: dict = st.dataframe(
            data=issue_displays,
            use_container_width=True,
            hide_index=True,
            column_order=[
                #'issue_id',
                'issue_dt',
                'is_reissue',
                'num_shares',
                'issue_price',
            ],
            column_config={
                'issue_dt': st.column_config.DateColumn(
                    label='Issue Date',
                    width=None,
                    pinned=True,
                ),
                'is_reissue': st.column_config.CheckboxColumn(
                    label='Reissue',
                    width=None,
                ),
                'num_shares': st.column_config.NumberColumn(
                    label='# Shares',
                    width=None,
                    format='%.3f',
                    step=0.0001
                ),
                'issue_price': st.column_config.NumberColumn(
                    label=f'Issue Price ({base_cur_name})',
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
            iss_id_sel = issues[_row_list[0]]['issue_id']
            issue_sel, jrn_sel = get_issue_journal(iss_id_sel)
            
            badge_cols = st.columns([1, 2])
            with badge_cols[0]:
                ui.badges(
                    badge_list=[("Issue ID", "default"), (iss_id_sel, "secondary")], 
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
        st.warning(f"No issues found", icon='🥵')


# either add mode or selected edit/view mode
if edit_mode == 'Add' or (edit_mode == 'Edit' and len(issues) > 0 and _row_list):
    
    is_reissue = st.toggle(
        label='Reissue of treasury stock?',
        value=False if edit_mode == 'Add' else issue_sel['is_reissue'],
        disabled=(edit_mode == 'Edit' or len(repurs) == 0),
        on_change=reset_validate
    )
    if len(repurs) == 0:
        st.warning('Add at least a repurchase to unlock reissue stock', icon='🤔')
    
    reiss_cols = st.columns(2)
    with reiss_cols[0]:
        issue_dt = st.date_input(
            label='📅 Issue Date',
            value=date.today() if edit_mode == 'Add' else issue_sel['issue_dt'],
            key=f'date_input',
            disabled=False,
            on_change=reset_validate
        )
    
    if is_reissue:  
        with reiss_cols[1]:
            
            if edit_mode == 'Add':
                repur_idx = st.selectbox(
                    label='🫙 Reissue which treasury stock batch',
                    options=dds_repurs.options,
                    key='repur_select',
                    index=0,
                    disabled=False,
                    on_change=reset_validate
                )
            elif edit_mode == 'Edit':
                repur_idx = st.selectbox(
                    label='🫙 Reissue which treasury stock batch',
                    options=dds_repurs.options,
                    key='repur_select',
                    index=dds_repurs.get_idx_from_id(issue_sel['reissue_repur_id']),
                    disabled=(edit_mode == 'Edit'),
                    on_change=reset_validate
                )
            
            repur_id = dds_repurs.get_id(repur_idx)
            total_reissued = get_total_reissue_from_repur(
                repur_id=repur_id,
                rep_dt=issue_dt,
                exclu_issue_id=None if edit_mode == 'Add' else iss_id_sel # must exclude itself
            )
            repur = list(filter(lambda r: r['repur_id'] == repur_id, repurs))[0]
            
        treasury_info = [
            {
                'Batch ID': repur_id,
                f'Cost': f"{base_cur_name} {repur['repur_price']:,.2f}",
                '# of Shares': repur['num_shares'],
                'Available': repur['num_shares'] - total_reissued
            }
        ]
        st.markdown(f'**Treasury Stock Summary**')
        ui.table(pd.DataFrame.from_records(treasury_info))
    
    iss_cols = st.columns(2)
    with iss_cols[0]:
        num_shares = st.number_input(
            label=f"#️⃣ # Shares",
            value=1.00 if edit_mode == 'Add' else issue_sel['num_shares'],
            max_value=None if not is_reissue else repur['num_shares'] - total_reissued,
            key='num_shares',
            on_change=reset_validate
        )
        
    with iss_cols[1]:
        issue_price = st.number_input(
            label=f"🏷️ Issue Price ({base_cur_name})",
            value=0.01 if edit_mode == 'Add' else issue_sel['issue_price'],
            step=0.01,
            key='issue_price',
            on_change=reset_validate
        )
    
    with iss_cols[0]:
        if edit_mode == 'Add':
            pmt_acct = st.selectbox(
                label='💳 Receiving Account',
                options=dds_pay_accts.options,
                key='acct_select',
                index=0,
                disabled=False,
                on_change=reset_validate
            )
        elif edit_mode == 'Edit':
            pmt_acct = st.selectbox(
                label='💳 Receiving Account',
                options=dds_pay_accts.options,
                key='acct_select2',
                index=dds_pay_accts.get_idx_from_id(issue_sel['debit_acct_id']),
                disabled=False,
                on_change=reset_validate
            )
            
        # get payment acct details
        pmt_acct_id = dds_pay_accts.get_id(pmt_acct)
        pmt_acct = get_account(pmt_acct_id, access_token=access_token)
        
    with iss_cols[1]:
        pmt_amt = st.number_input(
            label=f"💰 Received Amount ({CurType(pmt_acct['currency'] or get_base_currency()).name})",
            value=0.0 if edit_mode == 'Add' else issue_sel['issue_amt'],
            step=0.01,
            key='pmt_amt',
            on_change=reset_validate
        )
        
    note = st.text_input(
        label='📝 Note',
        value="" if edit_mode == 'Add' else issue_sel['note'],
        placeholder="payment note here",
    )
    
    
    # compile issues
    issue_ = {
        "issue_dt": issue_dt.strftime('%Y-%m-%d'), # convert to string
        "is_reissue": is_reissue,
        "reissue_repur_id": None if not is_reissue else repur_id,
        "num_shares": num_shares,
        "issue_price": issue_price,
        "debit_acct_id": pmt_acct_id,
        "issue_amt": pmt_amt,
        "note": None if note == "" else note,
    }
    # need this to validate bypass itself
    if edit_mode == 'Edit':
        issue_['issue_id'] = iss_id_sel

    # TODO: only validate if in add mode or if in edit mode and actually changed something
    validate_btn = st.button(
        label='Validate and Update Journal Entry Preview',
        on_click=validate_issue_,
        args=(issue_, )
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
            label='Add Issue',
            on_click=add_issue,
            args=(issue_,)
        )
        
    elif edit_mode == 'Edit':
        btn_cols = st.columns([1, 1, 5])
        with btn_cols[1]:
            if st.session_state.get('validated', False):
                # add invoice id to update
                st.button(
                    label='Update',
                    type='secondary',
                    on_click=update_issue,
                    args=(issue_,)
                )
        with btn_cols[0]:
            st.button(
                label='Delete',
                type='primary',
                on_click=delete_issue,
                kwargs=dict(
                    issue_id=iss_id_sel
                )
            )
    