import math
import time
import uuid
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import streamlit as st
import streamlit_shadcn_ui as ui
from datetime import datetime, date
from utils.tools import DropdownSelect
from utils.enums import CurType, EntryType, JournalSrc
from utils.apis import convert_to_base, get_fx, list_journal, get_journal, get_all_accounts, get_account
from utils.exceptions import OpNotPermittedError
    
def display_journal(jrn: dict) -> dict:
    return {
        'journal_id': jrn['journal_id'],
        'jrn_date': datetime.strptime(jrn['jrn_date'], '%Y-%m-%d'),
        'jrn_src': JournalSrc(jrn['jrn_src']).name,
        'num_entries': jrn['num_entries'],
        'total_base_amount': jrn['total_base_amount'],
        'acct_names': jrn['acct_names'],
        'note': jrn['note']
    }

    
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
        
def correct_entry(entry: dict) -> dict:
    # correct and populate fields automatically
    if 'acct_name' in entry:
        acct_id = dds_accts.get_id(entry['acct_name'])
        acct = get_account(acct_id)
        if acct['acct_type'] in (1, 2, 3):
            # balance sheet accounts
            entry['currency'] = CurType(acct['currency']).name
    
    if 'amount' in entry:
        # if has amount entered
        if entry.get('currency') == 'CAD': # TODO, switch to use base currency
            entry['amount_base'] = entry['amount']
        elif entry.get('currency') is not None:
            # if currency exist and not base currency, do live FX conversion for user
            if entry.get('amount_base') is None:
                # if amount base not exist or value is None
                # only do conversion if not present, not to override user input
                fx = convert_to_base(
                    amount = 1.0,
                    src_currency = CurType[entry['currency']].value,
                    cur_dt = jrn_date
                )
                entry['amount_base'] = entry['amount'] * fx
                
                if entry.get('description') in (None, ""):
                    entry['description'] = f"convert using fx={fx:.4f}"
                
    return entry

def validate_entry(entry: dict):
    if entry.get('acct_name') is None:
        raise OpNotPermittedError(
            message='Emty rows detected, please remove',
            details=f"Should not be any emty rows!",
        )
    
    acct_id = dds_accts.get_id(entry['acct_name'])
    acct = get_account(acct_id)
    if acct['acct_type'] in (1, 2, 3):
        if entry['currency'] != CurType(acct['currency']).name:
            OpNotPermittedError(
                message='Balance sheet Account should have predefined currency',
                details=f"{entry['acct_name']} should have currency {CurType(acct['currency']).name}",
            )
            
    if entry['currency'] == 'CAD':
        if entry['amount_base'] != entry['amount']:
            OpNotPermittedError(
                message='Base Amount not equal to Raw Amount when currency is CAD', # TODO
                details=f"{entry['acct_name']} should have same raw and base amount",
            )
    

def clear_entries_from_cache():
    if 'debit_entries' in st.session_state:
        del st.session_state['debit_entries']
    if 'credit_entries' in st.session_state:
        del st.session_state['credit_entries']

def validate_entries(debit_entries, credit_entries):
    for e in debit_entries:
        try:
            validate_entry(e)
        except OpNotPermittedError as e:
            ui.alert_dialog(
                show=True, # TODO
                title="[Debit Entry] " + e.message,
                description=e.details,
                confirm_label="OK",
                cancel_label="Cancel",
                key=str(uuid.uuid1())
            )
            return # need to return
        
    for e in credit_entries:
        try:
            validate_entry(e)
        except OpNotPermittedError as e:
            ui.alert_dialog(
                show=True, # TODO
                title="[Credit Entry] " + e.message,
                description=e.details,
                confirm_label="OK",
                cancel_label="Cancel",
                key=str(uuid.uuid1())
            )
            return # need to return
    
    # validate total debit and total credit
    total_debits = get_total_amount_base(debit_entries)
    total_credits = get_total_amount_base(credit_entries)
    if not math.isclose(total_debits, total_credits):
        ui.alert_dialog(
            show=True,
            title='Total Debit and Credit does not match',
            description=f"Total Debit: {total_debits} while Total Credit: {total_credits}",
            confirm_label="OK",
            cancel_label="Cancel",
            key='alert_trial'
        )
        return
    
    ui.alert_dialog(
        show=True,
        title='Success!',
        description=f"Everything looks good!",
        confirm_label="OK",
        cancel_label="Cancel",
        key='alert_suc'
    )

def get_total_amount_base(entries):
    return sum(
        e['amount_base'] 
        for e in entries
        if pd.notnull(e['amount_base'])
    )

def on_change_data_editor(key_name: str, session_key: str):
    # get changes from data editor
    state = st.session_state[key_name]
    # print(f"Rows edited: {state['edited_rows']}")
    # print(f"Rows added: {state['added_rows']}")
    # print(f"Rows deleted: {state['deleted_rows']}")
    
    # merge the change state with current entries
    #merged_credit_entries = st.session_state[session_key].copy()
    # edit
    for index, updates in state["edited_rows"].items():
        st.session_state[session_key][index].update(updates)
    # add new row
    for new_row in state["added_rows"]:
        st.session_state[session_key].append(new_row)
    # delete row TODO: which comes first, add or delete
    for idx in sorted(state["deleted_rows"], reverse=True):
        # need to reversly delete, bc delete on update will get out of range error
        st.session_state[session_key].pop(idx)
    
    for i, e in enumerate(st.session_state[session_key]):
        new_e = correct_entry(e)
        # edit
        for k, v in new_e.items():
            st.session_state[session_key][i][k] = v


jrn_src_types = DropdownSelect.from_enum(
    JournalSrc,
    include_null=False
)

jrn_src_type_option = st.selectbox(
    label='📋 Journal Source',
    options=jrn_src_types.options,
    key='jrn_src_type_select'
)
jrn_src: JournalSrc = jrn_src_types.get_id(jrn_src_type_option)
jrns = list_journal(jrn_src=jrn_src.value)
jrn_displays = map(display_journal, jrns)

selected: dict = st.dataframe(
    data=jrn_displays,
    use_container_width=True,
    hide_index=True,
    column_order=[
        #'journal_id',
        'jrn_date',
        #'jrn_src',
        'num_entries',
        'total_base_amount',
        'acct_names',
        'note'
    ],
    column_config={
        # 'journal_id': st.column_config.TextColumn(
        #     label='Journal ID',
        #     width=None,
        #     pinned=True,
        # ),
        'jrn_date': st.column_config.DateColumn(
            label='Date',
            width=None,
            pinned=True,
        ),
        'jrn_src': st.column_config.SelectboxColumn(
            label='Source',
            width=None,
            options=jrn_src_types.options
        ),
        'num_entries': st.column_config.NumberColumn(
            label='Entries',
            width=None,
            format='%d'
        ),
        'total_base_amount': st.column_config.NumberColumn(
            label='$Amount',
            width=None,
            format='$ %.2f'
        ),
        'acct_names': st.column_config.ListColumn(
            label='Involved Accounts',
            width=None
        ),
        'note': st.column_config.TextColumn(
            label='Note',
            width=None,
        ),
    },
    on_select=clear_entries_from_cache, # TODO: callbale to show details maybe
    selection_mode=(
        'single-row',
    )
)

st.divider()

if _row_list := selected['selection']['rows']:
    jrn_id_sel = jrns[_row_list[0]]['journal_id']
    jrn_sel = get_journal(jrn_id_sel)
    #st.json(jrn_sel)
    
    badge_cols = st.columns([1, 2])
    with badge_cols[0]:
        ui.badges(
            badge_list=[("Journal ID", "default"), (jrn_id_sel, "secondary")], 
            class_name="flex gap-2", 
            key="badges1"
        )
    with badge_cols[1]:
        ui.badges(
            badge_list=[("Journal Source", "destructive"), (JournalSrc(jrn_sel['jrn_src']).name, "secondary")], 
            class_name="flex gap-2", 
            key="badges2"
        )
    
    jrn_date = st.date_input(
        label='Journal Date',
        value=jrn_sel['jrn_date'],
        key=f'date_input',
        disabled=(jrn_src!=JournalSrc.MANUAL)
    )
    
    # prepare data editor
    all_accts = get_all_accounts()
    dds_accts = DropdownSelect(
        briefs=all_accts,
        include_null=False,
        id_key='acct_id',
        display_keys=['acct_name']
    )
    
    dds_currency = DropdownSelect.from_enum(
        CurType,
        include_null=False
    )
    
    jhelper = JournalEntryHelper(jrn_sel)
    
    if 'debit_entries' not in st.session_state:
        st.session_state['debit_entries'] = jhelper.debit_entries
    if 'credit_entries' not in st.session_state:
        st.session_state['credit_entries'] = jhelper.credit_entries
    
    debit_container = st.container(border=True)
    debit_container.caption('Debit Entries')
    debit_entries = debit_container.data_editor(
        #data=st.session_state.get('debit_entries', jhelper.debit_entries),
        data=st.session_state['debit_entries'],
        num_rows='dynamic',
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
                #required=True
            ),
            'amount_base': st.column_config.NumberColumn(
                label='Base Amt',
                width=None,
                format='$ %.2f',
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
        #key=st.session_state.get('key_debit_editor', str(uuid.uuid4()))
        disabled=(jrn_src!=JournalSrc.MANUAL),
        on_change=on_change_data_editor,
        kwargs={
            'key_name': 'key_editor_debit',
            'session_key': 'debit_entries'
        }
    )
    
    credit_container = st.container(border=True)
    credit_container.caption('Credit Entries')
    credit_entries = credit_container.data_editor(
        #data=st.session_state.get('credit_entries', jhelper.credit_entries),
        data=st.session_state['credit_entries'],
        num_rows='dynamic',
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
                #required=True
            ),
            'amount_base': st.column_config.NumberColumn(
                label='Base Amt',
                width=None,
                format='$ %.2f',
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
        #key=st.session_state.get('key_credit_editor', str(uuid.uuid4()))
        disabled=(jrn_src!=JournalSrc.MANUAL),
        on_change=on_change_data_editor,
        kwargs={
            'key_name': 'key_editor_credit',
            'session_key': 'credit_entries'
        }
    )
    
    #validate_entries(debit_entries, credit_entries)
    #st.json(debit_entries)
    total_debit = get_total_amount_base(debit_entries)
    #debit_container.json(debit_entries)
    debit_container.markdown(f'📥 **Total Debit**: :green-background[{total_debit:.2f}]')
    total_credit = get_total_amount_base(credit_entries)
    #credit_container.json(credit_entries)
    credit_container.markdown(f'📤 **Total Credit**: :blue-background[{total_credit:.2f}]')
    
    if jrn_src == JournalSrc.MANUAL:
        validate_btn = st.button(
            label='Validate',
            on_click=validate_entries,
            args=(debit_entries, credit_entries)
        )