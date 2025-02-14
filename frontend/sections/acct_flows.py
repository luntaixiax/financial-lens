from datetime import date, datetime, timedelta
from collections import OrderedDict
from typing import Tuple
import uuid
import streamlit as st
import streamlit_shadcn_ui as ui
from utils.apis import get_account, get_all_accounts, get_blsh_balance, get_incexp_flow, \
    get_base_currency, list_entry_by_acct
from utils.tools import DropdownSelect
from utils.enums import CurType, EntryType, AcctType

st.set_page_config(layout="centered")

def group_entries_by_dates(entries: list[dict], year: int) -> dict[int, dict[int, list[dict]]]:
    # group entries by month and day
    grouped = OrderedDict()
    for entry in entries:
        entry_dt = datetime.strptime(entry['jrn_date'], '%Y-%m-%d').date()
        if entry_dt.year != year:
            continue
        
        yr_mnth = entry_dt.year * 100 + entry_dt.month
        if yr_mnth not in grouped:
            grouped[yr_mnth] = OrderedDict({
                entry_dt.day: [entry] 
            })
        else:
            if entry_dt.day not in grouped[yr_mnth]:
                grouped[yr_mnth][entry_dt.day] = [entry]
            else:
                grouped[yr_mnth][entry_dt.day].append(entry)
    return grouped

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
            key=str(uuid.uuid4())
        )
        
    with balance_cols[1]:
        ui.metric_card(
            title=f" {debit_direction} (Dr)", 
            content=f"{blsh_summary['debit_amount_raw']:,.2f}", 
            description=f"# of entries: {blsh_summary['num_debit_entry']:d}", 
            key=str(uuid.uuid4())
        )
        
    with balance_cols[2]:
        ui.metric_card(
            title=f" {credit_direction} (Cr)", 
            content=f"{blsh_summary['credit_amount_raw']:,.2f}", 
            description=f"# of entries: {blsh_summary['num_credit_entry']:d}", 
            key=str(uuid.uuid4())
        )
    
    year = st.selectbox(
        label='Select Calendar Year',
        options=list(range(1970, date.today().year + 1)[::-1])
    )
    
    entries = list_entry_by_acct(acct_id)
        
    # list entries
    grped_entries = group_entries_by_dates(entries, year)
    if len(grped_entries) == 0:
        st.warning(f"No entry found for year {year}, try another year!", icon='🥵')
    
    for yr_mnth in grped_entries.keys():
        yr_mnth_dt = datetime(yr_mnth // 100, yr_mnth % 100, 1)
        with st.expander(label=f"**{yr_mnth_dt.strftime('%b %Y')}**", expanded=True, icon='📅'):
            # TODO: add monthly stat here
            mnth_end_dt = (yr_mnth_dt.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            flow_stat = get_incexp_flow(
                acct_id=acct_id,
                start_dt=yr_mnth_dt,
                end_dt=mnth_end_dt
            )
            flow_cols = st.columns([2, 1, 1], gap='small', border=False)
            with flow_cols[0]:
                ui.metric_card(
                    title="Net Flow", 
                    content=f"{CurType(acct['currency']).name} {flow_stat['net_raw']:,.2f}", 
                    description=f"As of {mnth_end_dt.date()}", 
                    key=str(uuid.uuid4())
                )
                
            with flow_cols[1]:
                ui.metric_card(
                    title=f" {debit_direction} (Dr)", 
                    content=f"{flow_stat['debit_amount_raw']:,.2f}", 
                    description=f"# of entries: {flow_stat['num_debit_entry']:d}", 
                    key=str(uuid.uuid4())
                )
                
            with flow_cols[2]:
                ui.metric_card(
                    title=f" {credit_direction} (Cr)", 
                    content=f"{flow_stat['credit_amount_raw']:,.2f}", 
                    description=f"# of entries: {flow_stat['num_credit_entry']:d}", 
                    key=str(uuid.uuid4())
                )
            
            for day, _ents in grped_entries[yr_mnth].items():
                with st.container(border=True):
                    col_entry = st.columns([1, 6])
                    with col_entry[0]:
                        dt = datetime(yr_mnth // 100, yr_mnth % 100, day)
                        st.metric(
                            label=dt.strftime("%A"),
                            value=dt.strftime("%d"),
                            delta=None
                        )
                    
                    with col_entry[1]:
                        for i, ent in enumerate(_ents):
                            if i != 0:
                                st.divider()
                            
                            if ent['entry_type'] == 1:
                                direction = 'Debit'
                                mutate = (1 if debit_direction == 'Inflow' else -1)
                            
                            else:
                                direction = 'Credit'
                                mutate = (1 if credit_direction == 'Inflow' else -1)
                                
                            amount_raw = mutate * ent['amount_raw']
                            if amount_raw < 0:
                                color = "#FF033E"
                                bg_color = 'red'
                            else:
                                color = '#008000'
                                bg_color = 'green'

                            st.markdown(
                                body=f"**:grey[Entry ID]**: :grey[{ent['entry_id']}] | **:grey[Journal ID]**: :grey[{ent['journal_id']}] | **:{bg_color}-background[{direction}]**",
                            )
                            
                            cols = st.columns([2, 1], vertical_alignment='bottom')
                            with cols[0]:
                                
                                amount_str = r"$\text{\small  " + f"{CurType(acct['currency']).name} " + r"\large \textcolor{" + color + "}{" + f"{amount_raw:,.2f}" +  r" }}$"
                                st.markdown(amount_str)
                            
                            with cols[1]:
                                base_amount_str = r"$\text{\small Balance: \ \ " + r"\normalsize " + f"{ent['cum_acount_raw']:,.2f}" +  r" }$"
                                st.markdown(base_amount_str)
                            
                            if ent['description'] is not None:
                                st.text_area(label="Note", value=ent['description'], disabled=True, height=70, key=str(uuid.uuid4()))
    
    
else:
    debit_direction = "Inflow" if acct['acct_type'] in (5, ) else "Outflow"
    credit_direction = "Inflow" if acct['acct_type'] in (4, ) else "Outflow"
            
    year = st.selectbox(
        label='Select Calendar Year',
        options=list(range(1970, date.today().year + 1)[::-1])
    )
    
    # show YTD statistics
    incexp_summary_ytd = get_incexp_flow(
        acct_id=acct_id,
        start_dt=date(year, 1, 1), # year start
        end_dt=date(year, 12, 31), # year end
    )
    flow_cols = st.columns([2, 1, 1], gap='small', border=False)
    with flow_cols[0]:
        ui.metric_card(
            title="YTD Cash Flow", 
            content=f"{CurType(base_cur).name} {incexp_summary_ytd['net_base']:,.2f}", 
            description=f"For Calendar Year {year}", 
            key=str(uuid.uuid4())
        )
        
    with flow_cols[1]:
        ui.metric_card(
            title=f" {debit_direction} (Dr)", 
            content=f"{incexp_summary_ytd['debit_amount_base']:,.2f}", 
            description=f"# of entries: {incexp_summary_ytd['num_debit_entry']:d}", 
            key=str(uuid.uuid4())
        )
        
    with flow_cols[2]:
        ui.metric_card(
            title=f" {credit_direction} (Cr)", 
            content=f"{incexp_summary_ytd['credit_amount_base']:,.2f}", 
            description=f"# of entries: {incexp_summary_ytd['num_credit_entry']:d}", 
            key=str(uuid.uuid4())
        )
    
    entries = list_entry_by_acct(acct_id)
        
    # list entries
    grped_entries = group_entries_by_dates(entries, year)
    if len(grped_entries) == 0:
        st.warning(f"No entry found for year {year}, try another year!", icon='🥵')
        
    for yr_mnth in grped_entries.keys():
        yr_mnth_dt = datetime(yr_mnth // 100, yr_mnth % 100, 1)
        with st.expander(label=f"**{yr_mnth_dt.strftime('%b %Y')}**", expanded=True, icon='📅'):
            # TODO: add monthly stat here
            mnth_end_dt = (yr_mnth_dt.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            flow_stat = get_incexp_flow(
                acct_id=acct_id,
                start_dt=yr_mnth_dt,
                end_dt=mnth_end_dt
            )
            flow_cols = st.columns([2, 1, 1], gap='small', border=False)
            with flow_cols[0]:
                ui.metric_card(
                    title="MTD Cash Flow", 
                    content=f"{CurType(base_cur).name} {flow_stat['net_base']:,.2f}", 
                    description=f"For {yr_mnth_dt.strftime('%b %Y')}", 
                    key=str(uuid.uuid4())
                )
                
            with flow_cols[1]:
                ui.metric_card(
                    title=f" {debit_direction} (Dr)", 
                    content=f"{flow_stat['debit_amount_base']:,.2f}", 
                    description=f"# of entries: {flow_stat['num_debit_entry']:d}", 
                    key=str(uuid.uuid4())
                )
                
            with flow_cols[2]:
                ui.metric_card(
                    title=f" {credit_direction} (Cr)", 
                    content=f"{flow_stat['credit_amount_base']:,.2f}", 
                    description=f"# of entries: {flow_stat['num_credit_entry']:d}", 
                    key=str(uuid.uuid4())
                )
            
            for day, _ents in grped_entries[yr_mnth].items():
                with st.container(border=True):
                    col_entry = st.columns([1, 6])
                    with col_entry[0]:
                        dt = datetime(yr_mnth // 100, yr_mnth % 100, day)
                        st.metric(
                            label=dt.strftime("%A"),
                            value=dt.strftime("%d"),
                            delta=None
                        )
                    
                    with col_entry[1]:
                        for i, ent in enumerate(_ents):
                            if i != 0:
                                st.divider()
                            
                            if ent['entry_type'] == 1:
                                direction = 'Debit'
                                mutate = (1 if debit_direction == 'Inflow' else -1)
                            
                            else:
                                direction = 'Credit'
                                mutate = (1 if credit_direction == 'Inflow' else -1)
                                
                            amount_raw = mutate * ent['amount_raw']
                            if amount_raw < 0:
                                color = "#FF033E"
                                bg_color = 'red'
                            else:
                                color = '#008000'
                                bg_color = 'green'

                            st.markdown(
                                body=f"**:grey[Entry ID]**: :grey[{ent['entry_id']}] | **:grey[Journal ID]**: :grey[{ent['journal_id']}] | **:{bg_color}-background[{direction}]**",
                            )
                            
                            cols = st.columns([2, 1], vertical_alignment='bottom')
                            with cols[0]:
                                
                                amount_str = r"$\text{\small  " + f"{CurType(ent['cur_incexp']).name} " + r"\large \textcolor{" + color + "}{" + f"{amount_raw:,.2f}" +  r" }}$"
                                st.markdown(amount_str)
                            
                            with cols[1]:
                                base_amount_str = r"$\text{\small (" + f"{CurType(base_cur).name}" + ") "  + r"\normalsize " + f"{ent['amount_base']:,.2f}" +  r" }$"
                                st.markdown(base_amount_str)
                            
                            if ent['description'] is not None:
                                st.text_area(label="Note", value=ent['description'], disabled=True, height=70)