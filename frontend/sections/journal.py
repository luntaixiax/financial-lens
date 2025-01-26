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
from utils.apis import convert_to_base, get_base_currency, list_journal, get_journal, \
    get_all_accounts, get_account, add_journal, delete_journal, update_journal, \
    stat_journal_by_src
from utils.exceptions import OpNotPermittedError

st.set_page_config(layout="centered")

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
    if entry.get('acct_name') is not None:
        acct_id = dds_accts.get_id(entry['acct_name'])
        acct = get_account(acct_id)
        if acct['acct_type'] in (1, 2, 3):
            # balance sheet accounts
            entry['currency'] = CurType(acct['currency']).name
    
    if entry.get('amount') is not None:
        # if has amount entered
        if entry.get('currency') == CurType(get_base_currency()).name: # TODO, switch to use base currency
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
                entry['amount_base'] = round(entry['amount'] * fx, 2)
                
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
            
    if entry['currency'] == CurType(get_base_currency()).name:
        if entry['amount_base'] != entry['amount']:
            OpNotPermittedError(
                message=f'Base Amount not equal to Raw Amount when currency is {CurType(get_base_currency()).name}', # TODO
                details=f"{entry['acct_name']} should have same raw and base amount",
            )

def convert_entry_to_db(entry: dict, entry_type: EntryType):
    return {
        'entry_type': entry_type.value,
        'acct_id': dds_accts.get_id(entry['acct_name']), # convert to acct in apis
        'cur_incexp': CurType[entry['currency']].value, # convert to None for balance sheet item in apis
        'amount': entry['amount'],
        'amount_base': entry['amount_base'],
        'description': entry['description'],
    }


def clear_entries_from_cache():
    st.session_state['validated'] = False
    if 'debit_entries' in st.session_state:
        del st.session_state['debit_entries']
    if 'credit_entries' in st.session_state:
        del st.session_state['credit_entries']

def clear_entries_and_reset_page():
    clear_entries_from_cache()
    reset_page()

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
    st.session_state['validated'] = True # set to validated

def get_total_amount_base(entries):
    return sum(
        e['amount_base'] 
        for e in entries
        if pd.notnull(e['amount_base'])
    )

def on_change_data_editor(key_name: str, session_key: str):
    # clear validate status if any change
    st.session_state['validated'] = False
    
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

def reset_page():
    if 'search_page' in st.session_state:
        del st.session_state['search_page']

def increment_page():
    st.session_state['search_page'] += 1
    
def decrement_page():
    st.session_state['search_page'] -= 1
    
def navigate_to_page(page: int):
    st.session_state['search_page'] = page

tabs = st.tabs(['Overview', 'Manage Journal'])
with tabs[0]:

    # display metric card
    stat_jrn_by_src = stat_journal_by_src()
    count_all_jrns = sum(s[0] for s in stat_jrn_by_src.values())
    amount_all_jrns = sum(s[1] for s in stat_jrn_by_src.values())

    metric1_cols = st.columns(2)
    with metric1_cols[0]:
        ui.metric_card(
            title="Total Base Amount", 
            content=f"${amount_all_jrns:,.2f}", 
            description=f"All journals combined", 
            key="card1"
        )
    with metric1_cols[1]:
        ui.metric_card(
            title="# of Journals", 
            content=f"{count_all_jrns:,.0f}", 
            description=f"All journals combined", 
            key="card2"
        )

    metric2_cols = st.columns(len(JournalSrc))
    for i, jrn_src_ in enumerate(JournalSrc):
        with metric2_cols[i]:
            ui.metric_card(
                title=f"{jrn_src_.name}", 
                content=f"{stat_jrn_by_src.get(jrn_src_.value, [0, 0])[0]:,.0f}", 
                description=f"${stat_jrn_by_src.get(jrn_src_.value, [0, 0])[1]:,.2f}", 
                #key="card2"
            )
    
with tabs[1]:
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

    all_accts = get_all_accounts()
    dds_accts = DropdownSelect(
        briefs=all_accts,
        include_null=False,
        id_key='acct_id',
        display_keys=['acct_name']
    )
        
    if edit_mode == 'Edit':
        
        jrn_src_types = DropdownSelect.from_enum(
            JournalSrc,
            include_null=False
        )
        
        search_cols = st.columns([1, 3])
        with search_cols[0]:
            jrn_src_type_option = st.selectbox(
                label='📋 Journal Source',
                options=jrn_src_types.options,
                key='jrn_src_type_select',
                on_change=reset_page
            )
            jrn_src: JournalSrc = jrn_src_types.get_id(jrn_src_type_option)
        
        with search_cols[1]:
            # search for journal
            search_criterias = st.segmented_control(
                label='Search By',
                options=['Date', 'Amount', 'No. Entry', 'Account', 'Keyword', 'Journal ID'],
                selection_mode='multi',
                #default=['Date', 'Amount']
            )
        
        search_cols = st.columns([1, 3])
        with search_cols[0]:
            search_jrn_id = None
            if 'Journal ID' in search_criterias:
                search_jrn_id = st.text_input(
                    label='Journal ID',
                    key='search_jrn_id',
                    value=''
                )
        
        with search_cols[1]:
            search_note = ""
            if 'Keyword' in search_criterias:
                search_note = st.text_input(
                    label='Note Keyword',
                    value="",
                    placeholder='Keyword here',
                    key='search_keyword'
                )
        
        search_cols = st.columns([1, 3])
        with search_cols[0]:
            search_num_entries = None
            if 'No. Entry' in search_criterias:
                search_num_entries = st.number_input(
                    label='# Entries',
                    min_value=2,
                    max_value=25,
                    step=1,
                    key='search_no_entry'
                )
        
        with search_cols[1]:
            search_acct_names = None
            if 'Account' in search_criterias: 
                search_acct_names = st.multiselect(
                    label='Involved Accounts',
                    options=dds_accts.options,
                    key='search_acct_names'
                )
        
        search_cols = st.columns(2)
        # search by amount
        search_min_dt = date(1970, 1, 1)
        search_max_dt = date(2099, 12, 31)
        if 'Date' in search_criterias:
            with search_cols[0]:
                search_min_dt = st.date_input(
                    label='Min Journal Date',
                    value='today',
                    key='search_min_dt',
                )
            with search_cols[1]:
                search_max_dt = st.date_input(
                    label='Max Journal Date',
                    value='today',
                    key='search_max_dt',
                )
                
        # search by amount
        search_min_amount = -1
        search_max_amount = 9e8
        if 'Amount' in search_criterias:
            with search_cols[0]:
                search_min_amount = st.select_slider(
                    label='Min Base Amount',
                    options=[0, 10, 100, 1000, 10000, 100000, 1000000, 10000000],
                    value=0,
                    format_func=lambda x: '{:,.0f}'.format(x),
                    key='search_min_amount'
                )
            with search_cols[1]:
                search_max_amount = st.select_slider(
                    label='Max Base Amount',
                    options=[0, 10, 100, 1000, 10000, 100000, 1000000, 10000000],
                    value=10000000,
                    format_func=lambda x: '{:,.0f}'.format(x),
                    key='search_max_amount'
                )
        
        # save page to
        if 'search_page' not in st.session_state:
            st.session_state['search_page'] = 0
        
        PAGE_LIMIT = 25 # TODO: items per page
        
        jrns, num_jrns = list_journal(
            limit=PAGE_LIMIT,
            offset=st.session_state['search_page'] * PAGE_LIMIT, # page number
            jrn_src=jrn_src.value,
            jrn_ids=[search_jrn_id] if search_jrn_id else None,
            min_dt=search_min_dt,
            max_dt=search_max_dt,
            acct_names=search_acct_names,
            note_keyword=search_note,
            min_amount=search_min_amount,
            max_amount=search_max_amount,
            num_entries=search_num_entries
        )
        
        # prevent overflow (from cached)
        total_page = -(-num_jrns // PAGE_LIMIT)
        if total_page > 0 and st.session_state['search_page'] >= total_page:
            reset_page()
            st.rerun() # refresh
        
        if num_jrns > 0:
            
            st.info(f"Total journals found: {num_jrns}", icon='👏')
            
            MAX_PAGE_BTN = 7 # only be odd number (3, 5, 7, 9, etc...)
            info_btn_cols = st.columns(
                [1, 1] + [1 for i in range(MAX_PAGE_BTN)] + [1, 1], 
                vertical_alignment='center'
            )

            with info_btn_cols[0]:
                st.button(
                    label='',
                    icon='⏮',
                    #disabled=(st.session_state['search_page'] < 1),
                    key='first_btn',
                    on_click=navigate_to_page,
                    kwargs={'page': 0}
                )
                
            with info_btn_cols[1]:
                st.button(
                    label='',
                    icon='◀',
                    disabled=(st.session_state['search_page'] < 1),
                    key='prev_btn',
                    on_click=decrement_page
                )
            
            min_page_btn_num = max(
                0, min(
                    st.session_state['search_page'] - MAX_PAGE_BTN // 2, 
                    total_page - MAX_PAGE_BTN
                )
            )
            max_page_btn_num = min(
                total_page - 1, 
                max(
                    st.session_state['search_page'] + MAX_PAGE_BTN // 2, 
                    MAX_PAGE_BTN - 1
                )
            )
            #print(min_page_btn_num, max_page_btn_num)
            for i, pg in enumerate(range(min_page_btn_num, max_page_btn_num + 1)):
                with info_btn_cols[i + 2]: # bypass first 2 btns
                    st.button(
                        label=f'{pg + 1}',
                        #icon='⏭️',
                        disabled=(st.session_state['search_page'] == pg),
                        type='tertiary' if st.session_state['search_page'] == pg else 'secondary',
                        key=f'page_btn_{pg}',
                        on_click=navigate_to_page,
                        kwargs={'page': pg}
                    )
            
            with info_btn_cols[MAX_PAGE_BTN + 2]:
                st.button(
                    label='',
                    icon='▶',
                    disabled=(st.session_state['search_page'] >= total_page - 1),
                    key='next_btn',
                    on_click=increment_page
                )
                
            with info_btn_cols[MAX_PAGE_BTN + 3]:
                st.button(
                    label='',
                    icon='⏭',
                    #disabled=(st.session_state['search_page'] >= total_page - 1),
                    key='last_btn',
                    on_click=navigate_to_page,
                    kwargs={'page': total_page - 1}
                )
                
        else:
            st.warning(f"No journal found", icon='🥵')
        
        if num_jrns > 0:
            
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
                on_select=clear_entries_from_cache,
                selection_mode=(
                    'single-row',
                )
            )

            st.divider()

            if  _row_list := selected['selection']['rows']:
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

    # either add mode or selected edit/view mode
    if edit_mode == 'Add' or (edit_mode == 'Edit' and num_jrns > 0 and _row_list):
        disbale_edit = (edit_mode == 'Edit' and jrn_src!=JournalSrc.MANUAL)
        
        jrn_date = st.date_input(
            label='Journal Date',
            value=date.today() if edit_mode == 'Add' else jrn_sel['jrn_date'],
            key=f'date_input',
            disabled=disbale_edit
        )
        
        # prepare data editor
        dds_currency = DropdownSelect.from_enum(
            CurType,
            include_null=False
        )
        
        if edit_mode == 'Edit':
            # TODO: need to clear something in session state when switch from edit to add mode?
            jhelper = JournalEntryHelper(jrn_sel)
            default_debit_entries = jhelper.debit_entries
            default_credit_entries = jhelper.credit_entries
        else:
            default_debit_entries = [{c: None for c in [
                'acct_name',
                'currency',
                'amount',
                'amount_base',
                'description'
            ]}]
            default_credit_entries = [{c: None for c in [
                'acct_name',
                'currency',
                'amount',
                'amount_base',
                'description'
            ]}]
            
        if 'debit_entries' not in st.session_state:
            st.session_state['debit_entries'] = default_debit_entries
        if 'credit_entries' not in st.session_state:
            st.session_state['credit_entries'] = default_credit_entries
        
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
            #key=st.session_state.get('key_debit_editor', str(uuid.uuid4()))
            disabled=disbale_edit,
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
            #key=st.session_state.get('key_credit_editor', str(uuid.uuid4()))
            disabled=disbale_edit,
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
        debit_container.markdown(f'📥 **Total Debit ({CurType(get_base_currency()).name})**: :green-background[{total_debit:.2f}]')
        total_credit = get_total_amount_base(credit_entries)
        #credit_container.json(credit_entries)
        credit_container.markdown(f'📤 **Total Credit ({CurType(get_base_currency()).name})**: :blue-background[{total_credit:.2f}]')
        
        if not disbale_edit:
            validate_btn = st.button(
                label='Validate',
                on_click=validate_entries,
                args=(debit_entries, credit_entries)
            )
            
        note = st.text_input(
            label='🗒️ Note',
            value="" if edit_mode == 'Add' else jrn_sel['note'],
            key=f'note_input',
            disabled=disbale_edit
        )
        
        
        #st.json(journal)
        
        if edit_mode == 'Add':
            if st.session_state['validated']:
                # add button
                st.button(
                    label='Add Journal',
                    on_click=add_journal,
                    kwargs=dict(
                        jrn_date=jrn_date,
                        jrn_src=JournalSrc.MANUAL.value if edit_mode == 'Add' else jrn_src,
                        entries=[
                            convert_entry_to_db(e, entry_type=EntryType.DEBIT) 
                            for e in debit_entries
                        ] + [
                            convert_entry_to_db(e, entry_type=EntryType.CREDIT) 
                            for e in credit_entries
                        ],
                        note=note
                    )
                )
                
        elif not disbale_edit:
            # update and remove button
            btn_cols = st.columns([1, 1, 5])
            with btn_cols[1]:
                if st.session_state['validated']:
                    st.button(
                        label='Update',
                        type='secondary',
                        on_click=update_journal,
                        kwargs=dict(
                            jrn_id=jrn_id_sel,
                            jrn_date=jrn_date,
                            jrn_src=JournalSrc.MANUAL.value if edit_mode == 'Add' else jrn_src,
                            entries=[
                                convert_entry_to_db(e, entry_type=EntryType.DEBIT) 
                                for e in debit_entries
                            ] + [
                                convert_entry_to_db(e, entry_type=EntryType.CREDIT) 
                                for e in credit_entries
                            ],
                            note=note
                        )
                    )
            with btn_cols[0]:
                st.button(
                    label='Delete',
                    type='primary',
                    on_click=delete_journal,
                    kwargs=dict(
                        journal_id=jrn_id_sel
                    )
                )