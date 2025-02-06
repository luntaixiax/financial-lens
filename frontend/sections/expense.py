import math
import time
import uuid
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import streamlit as st
import streamlit_shadcn_ui as ui
from datetime import datetime, date
from utils.tools import DropdownSelect
from utils.enums import AcctType, CurType, EntryType, JournalSrc
from utils.apis import convert_to_base, get_base_currency, list_expense, get_expense_journal, \
    create_journal_from_new_expense, validate_expense, add_expense, update_expense, delete_expense, \
    get_default_tax_rate, get_accounts_by_type, get_all_accounts, get_account
    
st.set_page_config(layout="centered")

def display_exp(exp: dict) -> dict:
    return {
        'expense_id': exp['expense_id'],
        'expense_dt': datetime.strptime(exp['expense_dt'], '%Y-%m-%d'),
        'merchant': exp['merchant'],
        'currency': CurType(exp['currency']).name,
        'payment_acct_name': exp['payment_acct_name'],
        'total_raw_amount': exp['total_raw_amount'], # in expense currency
        'total_base_amount': exp['total_base_amount'],
        'expense_acct_names': exp['expense_acct_names'],
    }
    
def clear_entries_from_cache():
    st.session_state['validated'] = False

def reset_page():
    if 'search_page' in st.session_state:
        del st.session_state['search_page']

def increment_page():
    st.session_state['search_page'] += 1
    
def decrement_page():
    st.session_state['search_page'] -= 1
    
def navigate_to_page(page: int):
    st.session_state['search_page'] = page
        
def clear_entries_and_reset_page():
    clear_entries_from_cache()
    reset_page()

exp_accts = get_accounts_by_type(acct_type=AcctType.EXP.value)
dds_exp_accts = DropdownSelect(
    briefs=exp_accts,
    include_null=False,
    id_key='acct_id',
    display_keys=['acct_name']
)

ast_accts = get_accounts_by_type(acct_type=AcctType.AST.value)
lib_accts = get_accounts_by_type(acct_type=AcctType.LIB.value)
equ_accts = get_accounts_by_type(acct_type=AcctType.EQU.value)
dds_balsh_accts = DropdownSelect(
    briefs=ast_accts + lib_accts + equ_accts,
    include_null=False,
    id_key='acct_id',
    display_keys=['acct_name']
)

dds_currency = DropdownSelect.from_enum(
    CurType,
    include_null=False
)

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
    
    # add search bar
    search_criterias = st.segmented_control(
        label='Search By',
        options=['Date', 'Currency', 'Amount', 'PMT Acct', 'EXP Acct', 'Expense ID'],
        selection_mode='multi',
        #default=['Date', 'Amount']
    )
    
    search_cols = st.columns([1, 3])
    with search_cols[0]:
        search_exp_id = None
        if 'Expense ID' in search_criterias:
            search_exp_id = st.text_input(
                label='Expense ID',
                key='search_exp_id',
                value=''
            )
            
    with search_cols[1]:
        search_pmt_acct_name = None
        if 'PMT Acct' in search_criterias: 
            search_pmt_acct_name = st.selectbox(
                label='Payment Account',
                options=dds_balsh_accts.options,
                key='search_pmt_acct_name'
            )
            
    with search_cols[0]:
        search_currency = None
        if 'Currency' in search_criterias: 
            search_currency = st.selectbox(
                label='Expense Currency',
                options=dds_currency.options,
                key='search_currency'
            )
    
    with search_cols[1]:
        search_exp_acct_names = None
        if 'EXP Acct' in search_criterias: 
            search_exp_acct_names = st.multiselect(
                label='Expense Account(s)',
                options=dds_exp_accts.options,
                key='search_exp_acct_names'
            )
            
    search_cols = st.columns(2)
    # search by date
    search_min_dt = date(1970, 1, 1)
    search_max_dt = date(2099, 12, 31)
    if 'Date' in search_criterias:
        with search_cols[0]:
            search_min_dt = st.date_input(
                label='Min Exp Date',
                value='today',
                key='search_min_dt',
            )
        with search_cols[1]:
            search_max_dt = st.date_input(
                label='Max Exp Date',
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
    
    exps, num_exps = list_expense(
        limit=PAGE_LIMIT,
        offset=st.session_state['search_page'] * PAGE_LIMIT, # page number
        expense_ids=[search_exp_id] if search_exp_id else None,
        min_dt=search_min_dt,
        max_dt=search_max_dt,
        currency=CurType[search_currency].value if search_currency else None,
        payment_acct_name=search_pmt_acct_name,
        expense_acct_names=search_exp_acct_names,
        min_amount=search_min_amount,
        max_amount=search_max_amount,
    )
    
    # prevent overflow (from cached)
    total_page = -(-num_exps // PAGE_LIMIT)
    if total_page > 0 and st.session_state['search_page'] >= total_page:
        reset_page()
        st.rerun() # refresh
        
    if num_exps > 0:
        
        st.info(f"Total expenses found: {num_exps}", icon='👏')
        
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
        st.warning(f"No expense found", icon='🥵')
        
    if num_exps > 0:
        
        exp_displays = map(display_exp, exps)
        
        selected: dict = st.dataframe(
            data=exp_displays,
            use_container_width=True,
            hide_index=True,
            column_order=[
                #'journal_id',
                'expense_dt',
                'merchant',
                'currency',
                'total_raw_amount',
                'expense_acct_names',
                'payment_acct_name',
            ],
            column_config={
                'expense_dt': st.column_config.DateColumn(
                    label='Date',
                    width=None,
                    pinned=True,
                ),
                'merchant': st.column_config.TextColumn(
                    label='Merchant',
                    width=None,
                ),
                'currency': st.column_config.SelectboxColumn(
                    label='Exp Cur',
                    width=None,
                    options=dds_currency.options
                ),
                'total_raw_amount': st.column_config.NumberColumn(
                    label='Amount',
                    width=None,
                    format='$ %.2f'
                ),
                'expense_acct_names': st.column_config.ListColumn(
                    label='Exp Accts',
                    width=None
                ),
                'payment_acct_name': st.column_config.SelectboxColumn(
                    label='PMT Acct',
                    width=None,
                    options=dds_balsh_accts.options
                ),

            },
            on_select=clear_entries_from_cache,
            selection_mode=(
                'single-row',
            )
        )
        
        st.divider()

        if  _row_list := selected['selection']['rows']:
            exp_id_sel = exps[_row_list[0]]['expense_id']
            exp_sel, jrn_sel = get_expense_journal(exp_id_sel)
            
            badge_cols = st.columns([1, 2])
            with badge_cols[0]:
                ui.badges(
                    badge_list=[("Expense ID", "default"), (exp_id_sel, "secondary")], 
                    class_name="flex gap-2", 
                    key="badges1"
                )
            with badge_cols[1]:
                ui.badges(
                    badge_list=[("Journal ID", "destructive"), (jrn_sel['journal_id'], "secondary")], 
                    class_name="flex gap-2", 
                    key="badges2"
                )
