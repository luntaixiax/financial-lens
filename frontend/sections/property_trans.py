import math
import time
import uuid
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit.components.v1 as components
from datetime import datetime, date, timedelta
from utils.apis import list_property, get_account, get_property_journal, \
    get_all_accounts, get_base_currency, get_property_stat, list_property_trans, \
    get_propertytrans_journal, validate_property_trans, create_journal_from_new_property_trans, \
    add_property_trans, update_property_trans, delete_property_trans, get_comp_contact, get_logo
from utils.enums import PropertyType, PropertyTransactionType, CurType, AcctType, EntryType
from utils.tools import DropdownSelect

st.set_page_config(layout="centered")
with st.sidebar:
    comp_name, _ = get_comp_contact()
    
    st.markdown(f"Hello, :rainbow[**{comp_name}**]")
    st.logo(get_logo(), size='large')
    
    
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
    
def display_trans(trans: dict) -> dict:
    return {
        'trans_id': trans['trans_id'],
        'trans_dt': trans['trans_dt'],
        'trans_type': PropertyTransactionType(trans['trans_type']).name,
        'trans_amount': trans['trans_amount'],
    }

def validate_property_trans_(trans_: dict) -> dict:
    if trans_['trans_dt'] is None:
        ui.alert_dialog(
            show=True, # TODO
            title="Transaction Date is missing",
            description='Must assign a transaction date',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    if trans_['trans_type'] in (None, ""):
        ui.alert_dialog(
            show=True, # TODO
            title="Transaction type is missing",
            description='Must assign a type',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    if trans_['trans_amount'] == 0:
        ui.alert_dialog(
            show=True, # TODO
            title="Transaction value must not be zero",
            description='Must assign a non-zero value',
            confirm_label="OK",
            cancel_label="Cancel",
            key=str(uuid.uuid1())
        )
        return
    
    trans_ = validate_property_trans(trans_)
    if isinstance(trans_, dict):
        st.session_state['validated'] = True
        
        # calculate and journal to session state
        jrn_ = create_journal_from_new_property_trans(trans_)
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

properties = list_property()

if len(properties) > 0:
    dds_property = DropdownSelect(
        briefs=properties,
        include_null=False,
        id_key='property_id',
        display_keys=['property_id', 'property_name']
    )
    dds_property_trans = DropdownSelect.from_enum(
        enum_cls=PropertyTransactionType,
        include_null=False
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

    edit_property = st.selectbox(
        label='👇 Select Property',
        options=dds_property.options,
        index=0
    )
    existing_property_id = dds_property.get_id(edit_property)

    # TODO: list property value curve through time
    prop_sel, prop_jrn = get_property_journal(existing_property_id)
    pur_dt = datetime.strptime(prop_sel['pur_dt'], '%Y-%m-%d').date()
    cur_dt = datetime.now().date()
    acct = get_account(prop_sel['pur_acct_id'])
    currency = CurType(acct['currency']).name
    # list transactions
    prop_trans = list_property_trans(existing_property_id)

    # add key date points to transaction history
    trans_curve = [{
        'event_dt': pur_dt,
        'bool_value': prop_sel['pur_cost'],
    }]
    trans_events = [{
        'event': 'PURCHASE',
        'event_dt':pur_dt,
        'amount': prop_sel['pur_cost'],
    }]
    for prop_tran in prop_trans:
        event_dt = datetime.strptime(prop_tran['trans_dt'], '%Y-%m-%d').date()
        trans_events.append({
            'event': PropertyTransactionType(prop_tran['trans_type']).name,
            'event_dt': event_dt,
            'amount': (1 if prop_tran['trans_type'] in (3, ) else -1) * prop_tran['trans_amount'],
        })
        # add each accumulative value at each key date
        trans_stat = get_property_stat(existing_property_id, rep_dt=event_dt)
        trans_curve.append({
            'event_dt': event_dt,
            'bool_value': trans_stat['value'],
        })
        
    trans_events = sorted(trans_events, key=lambda x: x['event_dt'])
    trans_curve = sorted(trans_curve, key=lambda x: x['event_dt'])

    st.markdown("Transaction history")
    st.bar_chart(
        data=trans_events,
        x='event_dt',
        y='amount',
        color='event',
        use_container_width=True,
        height=250,
        x_label='Transaction Date',
        y_label=f'Amount ({currency})'
    )
    st.markdown("Book Value over time")
    st.line_chart(
        data=trans_curve,
        x='event_dt',
        y='bool_value',
        use_container_width=True,
        height=200,
        x_label='Evaluation Date',
        y_label=f'Book Value ({currency})'
    )
    # show cumulative value
    trans_stat = get_property_stat(existing_property_id, rep_dt=datetime.now().date())
    trans_stat_display = pd.DataFrame.from_records([{
        'Purchase Cost': f"{currency} {round(trans_stat['pur_cost'], 2):,.2f}",
        'Acc. Appreciation': f"{currency} {round(trans_stat['acc_appreciation'], 2):,.2f}",
        'Acc. Depreciation': f"{currency} {round(trans_stat['acc_depreciation'], 2):,.2f}",
        'Acc. Impairment': f"{currency} {round(trans_stat['acc_impairment'], 2):,.2f}",
        'Book Value': f"{currency} {round(trans_stat['value'], 2):,.2f}",
    }])
    ui.table(trans_stat_display)
    

    st.subheader("Manage Transactions")
    # list transaction as table to edit
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
        trans_displays = map(display_trans, prop_trans)
        if len(prop_trans) > 0:
            selected: dict = st.dataframe(
                data=trans_displays,
                use_container_width=True,
                hide_index=True,
                column_order=[
                    'trans_id',
                    'trans_dt',
                    'trans_type',
                    'trans_amount',
                ],
                column_config={
                    'trans_id': st.column_config.TextColumn(
                        label='Transaction Id',
                        width=None,
                    ),
                    'trans_dt': st.column_config.DateColumn(
                        label='Transaction Date',
                        width=None,
                        #pinned=True,
                    ),
                    'trans_type': st.column_config.SelectboxColumn(
                        label='Transaction Type',
                        width=None,
                        options=dds_property_trans.options
                    ),
                    'trans_amount': st.column_config.NumberColumn(
                        label='Amount',
                        width=None,
                        format='$ %.2f',
                        step=0.001
                    )
                },
                on_select=clear_entries_from_cache,
                selection_mode=(
                    'single-row',
                )
            )
            
            # if selected, show update widgets
            st.divider()
            
            if  _row_list := selected['selection']['rows']:
                trans_id_sel = prop_trans[_row_list[0]]['trans_id']
                trans_sel, jrn_sel = get_propertytrans_journal(trans_id_sel)
                
                if not 'journal' in st.session_state:
                    st.session_state['journal'] = jrn_sel
                
                badge_cols = st.columns([1, 2])
                with badge_cols[0]:
                    ui.badges(
                        badge_list=[("Transaction ID", "default"), (trans_id_sel, "secondary")], 
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
            st.warning(f"No property transaction found", icon='🥵')
            
    # either add mode or selected edit/view mode
    if edit_mode == 'Add' or (edit_mode == 'Edit' and len(prop_trans) > 0 and _row_list):
        
        wid_cols = st.columns(3)
        
        with wid_cols[0]:
            trans_date = st.date_input(
                label='📅 Transaction Date',
                value=date.today() if edit_mode == 'Add' else trans_sel['trans_dt'],
                key=f'date_input',
                disabled=False,
                on_change=reset_validate
            )
        with wid_cols[1]:
            if edit_mode == 'Add':
                trans_type = st.selectbox(
                    label='💳 Transaction Type',
                    options=dds_property_trans.options,
                    key='trans_type_select',
                    index=0,
                    disabled=False,
                    on_change=reset_validate
                )
            elif edit_mode == 'Edit':
                trans_type = st.selectbox(
                    label='💳 Transaction Type',
                    options=dds_property_trans.options,
                    key='trans_type_select',
                    index=dds_property_trans.get_idx_from_id(trans_sel['trans_type']),
                    disabled=False,
                    on_change=reset_validate
                )
        with wid_cols[2]:
            trans_amt = st.number_input(
                label=f"💰 Transaction Amount ({currency})",
                value=0.0 if edit_mode == 'Add' else trans_sel['trans_amount'],
                step=0.01,
                key='trans_amt',
                on_change=reset_validate
            )
        
        # compile property transaction object
        property_trans_ = {
            "property_id": existing_property_id,
            "trans_type": PropertyTransactionType[trans_type].value,
            "trans_dt": trans_date.strftime('%Y-%m-%d'), # convert to string
            "trans_amount": trans_amt,
        }
        
        validate_btn = st.button(
            label='Validate and Update Journal Entry Preview',
            on_click=validate_property_trans_,
            args=(property_trans_, )
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
                st.markdown(f'📤 **Total Credit ({CurType(get_base_currency()).name})**: :blue-background[{total_credit:.2f}]')

        
        if edit_mode == 'Add' and st.session_state.get('validated', False):
            # add button
            st.button(
                label='Add Transaction',
                on_click=add_property_trans,
                args=(property_trans_, )
            )
            
        elif edit_mode == 'Edit':
            btn_cols = st.columns([1, 1, 5])
            with btn_cols[1]:
                if st.session_state.get('validated', False):
                    property_trans_.update({'trans_id': trans_id_sel})
                    st.button(
                        label='Update',
                        type='secondary',
                        on_click=update_property_trans,
                        args=(property_trans_, )
                    )
            with btn_cols[0]:
                st.button(
                    label='Delete',
                    type='primary',
                    on_click=delete_property_trans,
                    kwargs=dict(
                        trans_id=trans_id_sel
                    )
                )
            
else:
    st.warning(f"No property found, please add one in **Buy Property** page", icon='🥵')