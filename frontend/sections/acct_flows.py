from datetime import date
import streamlit as st
import streamlit_shadcn_ui as ui
from utils.apis import get_account, get_all_accounts, get_blsh_balance, get_incexp_flow, \
    get_base_currency, list_entry_by_acct
from utils.tools import DropdownSelect
from utils.enums import CurType, EntryType, AcctType

all_accts = get_all_accounts()
acct_options = [
    {
        'acct_id': a['acct_id'],
        'acct_name': a['acct_name'],
        'acct_type': AcctType(a['acct_type']).name,
        'currency': CurType(a['currency']).name if a['currency'] else '-'
    }
    for a in all_accts
]
dds_accts = DropdownSelect(
    briefs=acct_options,
    include_null=False,
    id_key='acct_id',
    display_keys=['acct_name']
)

acct_name = st.selectbox(
    label='Select Account',
    options=dds_accts.options,
    key='acct_name'
)
acct_id = dds_accts.get_id(acct_name)
acct = get_account(acct_id)
base_cur = get_base_currency()
entries = list_entry_by_acct(acct_id)

badge_cols = st.columns(4)
with badge_cols[0]:
    ui.badges(
        badge_list=[
            ("ID", "default"), 
            (acct_id, "secondary"),
        ], 
        class_name="flex gap-2", 
        key="badges1"
    )
    
with badge_cols[1]:
    ui.badges(
        badge_list=[
            ("Type", "default"), 
            (AcctType(acct['acct_type']).name, "secondary"),
        ], 
        class_name="flex gap-2", 
        key="badges2"
    )
    
if acct['currency']:
    with badge_cols[2]:
        ui.badges(
            badge_list=[
                ("Currency", "default"), 
                (CurType(acct['currency']).name, "secondary"),
            ], 
            class_name="flex gap-2", 
            key="badges3"
        )

if acct['is_system']:
    with badge_cols[3]:
        ui.badges(
            badge_list=[
                ('Sys Acct', "destructive")
            ], 
            class_name="flex gap-2", 
            key="badges4"
        )

if acct['acct_type'] in (1, 2, 3):
    
    blsh_summary = get_blsh_balance(
        acct_id=acct_id,
        report_dt=date.today()
    )
    debit_direction = "Inflow" if acct['acct_type'] in (1,) else "Outflow"
    credit_direction = "Inflow" if acct['acct_type'] in (2, 3) else "Outflow"
    
    balance_cols = st.columns([2, 1, 1], gap='small', border=False)
    with balance_cols[0]:
        ui.metric_card(
            title="Balance", 
            content=f"{CurType(acct['currency']).name} {blsh_summary['net_raw']:,.2f}", 
            description=f"As of {date.today()}", 
            key="card1"
        )
        
    with balance_cols[1]:
        ui.metric_card(
            title=f" {debit_direction} (Dr)", 
            content=f"{blsh_summary['debit_amount_raw']:,.2f}", 
            description=f"# of entries: {blsh_summary['num_debit_entry']:d}", 
            key="card2"
        )
        
    with balance_cols[2]:
        ui.metric_card(
            title=f" {credit_direction} (Cr)", 
            content=f"{blsh_summary['credit_amount_raw']:,.2f}", 
            description=f"# of entries: {blsh_summary['num_credit_entry']:d}", 
            key="card3"
        )
        
    # list entries
    for entry in entries:
        with st.expander(label = entry['jrn_date'], icon = '➕' if entry['entry_type'] == 1 else '➖'):
            st.json(entry)
    
    
    
    
else:
    debit_direction = "Inflow" if acct['acct_type'] in (5, ) else "Outflow"
    credit_direction = "Inflow" if acct['acct_type'] in (4, ) else "Outflow"
    
    stat_period = ui.tabs(
        options=['YTD', 'MTD'], 
        default_value='YTD', 
        key="kanaries"
    )
    if stat_period == 'YTD':
        incexp_summary_ytd = get_incexp_flow(
            acct_id=acct_id,
            start_dt=date.today().replace(month=1, day=1), # year start
            end_dt=date.today(),
        )
        flow_cols = st.columns([2, 1, 1], gap='small', border=False)
        with flow_cols[0]:
            ui.metric_card(
                title="Net Cash Flow", 
                content=f"{CurType(base_cur).name} {incexp_summary_ytd['net_raw']:,.2f}", 
                description=f"As of {date.today()}", 
                key="card1"
            )
            
        with flow_cols[1]:
            ui.metric_card(
                title=f" {debit_direction} (Dr)", 
                content=f"{incexp_summary_ytd['debit_amount_raw']:,.2f}", 
                description=f"# of entries: {incexp_summary_ytd['num_debit_entry']:d}", 
                key="card2"
            )
            
        with flow_cols[2]:
            ui.metric_card(
                title=f" {credit_direction} (Cr)", 
                content=f"{incexp_summary_ytd['credit_amount_raw']:,.2f}", 
                description=f"# of entries: {incexp_summary_ytd['num_credit_entry']:d}", 
                key="card3"
            )
    else: # MTD
        incexp_summary_mtd = get_incexp_flow(
            acct_id=acct_id,
            start_dt=date.today().replace(day=1), # month start
            end_dt=date.today(),
        )
    
        flow_cols = st.columns([2, 1, 1], gap='small', border=False)
        with flow_cols[0]:
            ui.metric_card(
                title="Net Cash Flow", 
                content=f"{CurType(base_cur).name} {incexp_summary_mtd['net_raw']:,.2f}", 
                description=f"As of {date.today()}", 
                key="card1"
            )
            
        with flow_cols[1]:
            ui.metric_card(
                title=f" {debit_direction} (Dr)", 
                content=f"{incexp_summary_mtd['debit_amount_raw']:,.2f}", 
                description=f"# of entries: {incexp_summary_mtd['num_debit_entry']:d}", 
                key="card2"
            )
            
        with flow_cols[2]:
            ui.metric_card(
                title=f" {credit_direction} (Cr)", 
                content=f"{incexp_summary_mtd['credit_amount_raw']:,.2f}", 
                description=f"# of entries: {incexp_summary_mtd['num_credit_entry']:d}", 
                key="card3"
            )