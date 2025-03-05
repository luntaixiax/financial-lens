import math
import time
import io
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
    get_default_tax_rate, get_accounts_by_type, get_all_accounts, get_account, \
    upload_file, delete_file, get_file
    
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
    if 'exp_items' in st.session_state:
        del st.session_state['exp_items']

def reset_validate():
    st.session_state['validated'] = False

def reset_page():
    reset_validate()
    if 'search_page' in st.session_state:
        del st.session_state['search_page']

        
def clear_entries_and_reset_page():
    clear_entries_from_cache()
    reset_page()
    
def update_exp_item(entry: dict) -> dict:
    # whenever edited the table
    reset_validate()
    
    return entry
    
def on_change_exp_items():
    # whenever edited the table
    reset_validate()
    
    # get changes from data editor
    state = st.session_state['key_editor_exp_items']
    
    # edit
    for index, updates in state["edited_rows"].items():
        st.session_state['exp_items'][index].update(updates)
    # add new row
    for new_row in state["added_rows"]:
        st.session_state['exp_items'].append(new_row)
    # delete row TODO: which comes first, add or delete
    for idx in sorted(state["deleted_rows"], reverse=True):
        # need to reversly delete, bc delete on update will get out of range error
        st.session_state['exp_items'].pop(idx)
        
    for i, e in enumerate(st.session_state['exp_items']):
        new_e = update_exp_item(e)
        # edit
        for k, v in new_e.items():
            st.session_state['exp_items'][i][k] = v

def convert_exp_items_to_db(entries: list[dict]) -> list[dict]:
    items = []
    for e in entries:
        if e.get('expense_acct') is None:
            continue
        if e.get('amount_pre_tax') is None:
            continue
        if e.get('tax_rate') is None:
            continue
        
        r = {}
        r['expense_acct_id'] = dds_exp_accts.get_id(e.get('expense_acct'))
        r['amount_pre_tax'] = e['amount_pre_tax']
        r['tax_rate'] = e['tax_rate'] / 100
        
        items.append(r)
    return items

def validate_expense_(expense_: dict):
    if len(expense_['expense_items']) < 1:
        ui.alert_dialog(
            show=True, # TODO
            title="At least have one expense item",
            description='Have no items defined',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    # detect if payment key info is missing
    if expense_['currency'] in (None, ""):
        ui.alert_dialog(
            show=True, # TODO
            title="Currency is missing",
            description='Must assign a expense currency',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    if expense_['expense_dt'] is None:
        ui.alert_dialog(
            show=True, # TODO
            title="Expense Date is missing",
            description='Must assign a expense date',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    if expense_['payment_acct_id'] in (None, ""):
        ui.alert_dialog(
            show=True, # TODO
            title="Payment Account is missing",
            description='Must assign a payment account',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return

    expense_ = validate_expense(expense_)
    if isinstance(expense_, dict):
        if expense_.get('expense_items') is not None:
            st.session_state['validated'] = True
            
            # calculate and journal to session state
            jrn_ = create_journal_from_new_expense(expense_)
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

def increment_page():
    st.session_state['search_page'] += 1
    
def decrement_page():
    st.session_state['search_page'] -= 1
    
def navigate_to_page(page: int):
    st.session_state['search_page'] = page
        


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
                
# either add mode or selected edit/view mode
if edit_mode == 'Add' or (edit_mode == 'Edit' and _row_list):
    
    exp_cols = st.columns(2)
    with exp_cols[0]:
        exp_date = st.date_input(
            label='📅 Expense Date',
            value=date.today() if edit_mode == 'Add' else exp_sel['expense_dt'],
            key=f'date_input',
            disabled=False,
            on_change=reset_validate
        )
        pmt_acct = st.selectbox(
            label='💳 Payment Account',
            options=dds_balsh_accts.options,
            key='acct_select',
            index=0 if edit_mode == 'Add' else dds_balsh_accts.get_idx_from_id(exp_sel['payment_acct_id']),
            disabled=False,
            on_change=reset_validate
        )
        # get payment acct details
        pmt_acct_id = dds_balsh_accts.get_id(pmt_acct)
        pmt_acct = get_account(pmt_acct_id)
        
    with exp_cols[1]:
        cur_type_option = st.selectbox(
            label='💲 Currency',
            options=dds_currency.options,
            key='cur_type_select',
            index=0 if edit_mode == 'Add' else dds_currency.get_idx_from_id(exp_sel['currency']),
            on_change=reset_validate
        )
        pmt_amt = st.number_input(
            label=f"💰 Payment Amount ({CurType(pmt_acct['currency']).name})",
            value=0.0 if edit_mode == 'Add' else exp_sel['payment_amount'],
            step=0.01,
            key='pmt_amt',
            on_change=reset_validate
        )
    
    # expense items
    # prepare data editor
    if edit_mode == 'Edit':
        exp_items = [
            {
                'expense_acct': dds_exp_accts._mappings.get(pi['expense_acct_id']),
                'amount_pre_tax': pi['amount_pre_tax'],
                'tax_rate': pi['tax_rate'] * 100,
                'description': pi['description']
                
            } for pi in exp_sel['expense_items']
        ]
        
        if not 'journal' in st.session_state:
            st.session_state['journal'] = jrn_sel
    else:
        exp_items = [{c: None for c in [
            'expense_acct',
            'amount_pre_tax',
            'tax_rate',
            'description'
        ]}]
        exp_items[0]['tax_rate'] = get_default_tax_rate() * 100
    
    if 'exp_items' not in st.session_state:
        st.session_state['exp_items'] = exp_items
        
    exp_item_container = st.container(border=True)
    exp_item_container.subheader('Expense Items')
    exp_item_entries = exp_item_container.data_editor(
        #data=st.session_state['invoice_item_entries'], # TODO
        data=st.session_state['exp_items'],
        num_rows='dynamic',
        use_container_width=True,
        column_order=[
            'expense_acct',
            'amount_pre_tax',
            'tax_rate',
            'description'
        ],
        column_config={
            'expense_acct': st.column_config.SelectboxColumn(
                label='Exp Acct',
                width=None,
                options=dds_exp_accts.options,
                #required=True
            ),
            'amount_pre_tax': st.column_config.NumberColumn(
                label="Pretax Amount",
                width=None,
                format='$ %.2f',
                step=0.01,
                disabled=False
                #required=True
            ),
            'tax_rate': st.column_config.NumberColumn(
                label='Tax Rate',
                width=None,
                format='%.1f%%',
                step=0.1,
                min_value=0.0,
                max_value=100.0,
                default=get_default_tax_rate() * 100,
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
        key='key_editor_exp_items',
        disabled=False,
        on_change=on_change_exp_items,
    )
    
    subtotal = sum(e['amount_pre_tax'] or 0 for e in exp_item_entries)
    tax = sum((e['amount_pre_tax'] or 0) * (e['tax_rate'] or 0) / 100 for e in exp_item_entries)
    
    exp_item_container.markdown(
        f"💲 **Subtotal**: {subtotal: .2f}"
        + f" ➕ **Tax**: {tax: .2f}"
        + f" 🟰 **Total ({cur_type_option})**: {subtotal + tax: .2f}"
    )
    
    
    exp_cols = st.columns(2)
    with exp_cols[0]:
        
        merchant = st.text_input(
            label='🏪 Merchant',
            value="" if edit_mode == 'Add' else exp_sel['merchant']['merchant'],
            placeholder="merchant here",
        )
        platform = st.text_input(
            label='🏬 Platform',
            value="" if edit_mode == 'Add' else exp_sel['merchant']['platform'],
            placeholder="platform here (e.g., Uber)",
        )
        ref_no = st.text_input(
            label='#️⃣ Reference #',
            value="" if edit_mode == 'Add' else exp_sel['merchant']['ref_no'],
            placeholder="reference number",
        )
        
        
    with exp_cols[1]:
        note = st.text_area(
            label='📝 Note',
            value="" if edit_mode == 'Add' else exp_sel['note'],
            placeholder="payment note here",
            height=205
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
    
    if edit_mode == 'Edit' and (recpt_ids := exp_sel['receipts']) is not None:
        receipts = []
        remove_receipts = []
        for recpt_id in recpt_ids:
            receipt = get_file(file_id = recpt_id)
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
        
    
    # compile expense (without receipts)
    expense_ = {
        #"payment_id": "string",
        "expense_dt": exp_date.strftime('%Y-%m-%d'), # convert to string
        "currency": CurType[cur_type_option].value,
        "expense_items": convert_exp_items_to_db(exp_item_entries),
        "payment_acct_id": pmt_acct_id,
        "payment_amount": pmt_amt,
        "merchant": {
            'merchant': None if merchant == "" else merchant,
            'platform': None if platform == "" else platform,
            'ref_no': None if ref_no == "" else ref_no,
        },
        "note": None if note == "" else note,
        "receipts": exp_sel['receipts'] if edit_mode == 'Edit' else None
    }
    
    
    
    # TODO: only validate if in add mode or if in edit mode and actually changed something
    validate_btn = st.button(
        label='Validate and Update Journal Entry Preview',
        on_click=validate_expense_,
        args=(expense_, )
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
            label='Add Expense',
            on_click=add_expense,
            args=(expense_, files)
        )
        
    elif edit_mode == 'Edit':
        btn_cols = st.columns([1, 1, 5])
        with btn_cols[1]:
            if st.session_state.get('validated', False):
                # add invoice id to update
                expense_.update({'expense_id': exp_id_sel})
                st.button(
                    label='Update',
                    type='secondary',
                    on_click=update_expense,
                    args=(expense_, files)
                )
        with btn_cols[0]:
            st.button(
                label='Delete',
                type='primary',
                on_click=delete_expense,
                kwargs=dict(
                    invoice_id=exp_id_sel
                )
            )