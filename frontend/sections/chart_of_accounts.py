import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit_nested_layout # need it for nested structure
import pandas as pd
from utils.enums import CurType, AcctType
from utils.apis import tree_charts, list_charts, get_chart, get_parent_chart, list_accounts_by_chart, \
    add_chart, update_move_chart, delete_chart, list_accounts_by_chart, get_account, \
    add_account, update_account, delete_account
from utils.tools import DropdownSelect

st.set_page_config(layout="centered")

st.subheader('Manage Chart of Accounts')

def show_expander(tree: dict):
    label = f"**{tree['name']}** &nbsp; | &nbsp; :violet-background[{tree['chart_id']}]"
    with st.expander(label=label, expanded=True, icon = '🟰'):
        st.empty()
        accts = list_accounts_by_chart(tree['chart_id'])
        accts = pd.DataFrame.from_records([
            {
                #'System': ,
                'Acct ID': ('⭐ ' if r['is_system'] else ' ') + r['acct_id'], 
                'Acct Name': r['acct_name'], 
                'Currency': CurType(r['currency']).name if r['currency'] is not None else '-',
                
            } 
            for r in accts
        ])
        if not accts.empty:
            ui.table(accts)
        if 'children' in tree:
            for child in tree['children']:
                show_expander(child)

chart_types = DropdownSelect.from_enum(
    AcctType,
    include_null=False
)
acct_type_option = st.selectbox(
    label='📋 Chart Type',
    options=chart_types.options,
    key='chart_type_select'
)
acct_type: AcctType = chart_types.get_id(acct_type_option)
has_currency = acct_type in (AcctType.AST, AcctType.LIB, AcctType.EQU)
    
tabs = st.tabs(['Chart of Accounts', 'Add/Edit Chart', 'Add/Edit Account'])
with tabs[0]:
    
    
    ast_charts = tree_charts(acct_type.value)
    show_expander(ast_charts)
    
with tabs[1]:
    
    charts = list_charts(acct_type.value)
    
    dds_charts = DropdownSelect(
        briefs=charts,
        include_null=False,
        id_key='chart_id',
        display_keys=['chart_id', 'name']
    )
    
    edit_cols = st.columns([1, 3])
    with edit_cols[0]:
        edit_mode = st.radio(
            label='Edit Mode',
            options=['Add', 'Edit'],
            horizontal=True,
        )
        
    if edit_mode == 'Edit':
        with edit_cols[1]:
            edit_chart_option = st.selectbox(
                label='👇 Select Chart',
                options=dds_charts.options,
                index=0,
                key='chart_select'
            )
        existing_chart_id = dds_charts.get_id(edit_chart_option)
        existing_chart = get_chart(existing_chart_id)
        existing_parent_chart = get_parent_chart(existing_chart_id)
        
    st.divider()
    
    if edit_mode == 'Edit':
        ui.badges(
            badge_list=[("Chart ID", "default"), (existing_chart_id, "secondary")], 
            class_name="flex gap-2", 
            key="badges1"
        )
    
    chart_name = st.text_input(
        label='📖 Chart Name',
        value="" if edit_mode == 'Add' else existing_chart['name'],
        type='default', 
        placeholder="chart name here", 
    )
    if edit_mode == 'Add':
        parent_chart_option = st.selectbox(
            label='👨‍👧 Parent Chart',
            options=dds_charts.options,
            index=0,
            key='parent_chart_select1'
        )
        parent_chart_id = dds_charts.get_id(parent_chart_option)
    else:
        if existing_parent_chart is not None:
            parent_chart_option = st.selectbox(
                label='👨‍👧 Parent Chart',
                options=dds_charts.options,
                index=dds_charts.get_idx_from_id(existing_parent_chart['chart_id']),
                key='parent_chart_select2'
            )
            parent_chart_id = dds_charts.get_id(parent_chart_option)
        else:
            parent_chart_option: None = st.selectbox(
                label='👨‍👧 Parent Chart',
                options=[None],
                disabled=True,
                key='parent_chart_select3'
            )
    
    if edit_mode == 'Add':
        # add button
        st.button(
            label='Add Chart',
            on_click=add_chart,
            kwargs=dict(
                chart=dict(
                    name=chart_name,
                    acct_type=acct_type.value
                ),
                parent_chart_id=parent_chart_id,
            )
        )
        
    else:
        # update and remove button
        btn_cols = st.columns([1, 1, 5])
        with btn_cols[0]:
            if existing_parent_chart is not None:
                st.button(
                    label='Update',
                    type='secondary',
                    on_click=update_move_chart,
                    kwargs=dict(
                        chart=dict(
                            chart_id=existing_chart_id,
                            name=chart_name,
                            acct_type=acct_type.value
                        ),
                        parent_chart_id=parent_chart_id,
                    )
                )
            else:
                st.button(
                    label='Update',
                    type='secondary',
                    disabled=True
                )
                
        with btn_cols[1]:
            st.button(
                label='Delete',
                type='primary',
                on_click=delete_chart,
                kwargs=dict(
                    chart_id=existing_chart_id
                )
            )
            
with tabs[2]:
    
    edit_cols = st.columns([1, 3])
    with edit_cols[0]:
        edit_mode = st.radio(
            label='Edit Mode',
            options=['Add', 'Edit'],
            horizontal=True,
            key='radio_acct'
        )
        
    if edit_mode == 'Edit':
        with edit_cols[1]:
            edit_acct_chart_option = st.selectbox(
                label='🔎 Search Account under Chart',
                options=dds_charts.options,
                index=0,
                key='acct_chart_select'
            )
            existing_acct_chart_id = dds_charts.get_id(edit_acct_chart_option)
            existing_acct_chart = get_chart(existing_acct_chart_id)
        
            accounts = list_accounts_by_chart(existing_acct_chart_id)
            accounts = [
                {
                    'acct_id': r['acct_id'], 
                    'acct_name': r['acct_name'], 
                    'currency': CurType(r['currency']).name if r['currency'] is not None else '-'
                } 
                for r in accounts
            ]
            dds_accts = DropdownSelect(
                briefs=accounts,
                include_null=False,
                id_key='acct_id',
                display_keys=['acct_id', 'acct_name', 'currency'] if has_currency else ['acct_id', 'acct_name']
            )
            edit_acct_option = st.selectbox(
                label='👇 Select Account',
                options=dds_accts.options,
                index=0,
                key='acct_select'
            )
            if edit_acct_option is not None:
                # possible no account under some chart
                existing_acct_id = dds_accts.get_id(edit_acct_option)
                existing_acct = get_account(existing_acct_id)
        
    st.divider()
    
    if (edit_mode == 'Edit' and edit_acct_option is not None) or edit_mode == 'Add':
        
        if edit_mode == 'Edit':
            badge_list=[
                ("Account ID", "default"), 
                (existing_acct_id, "secondary")
            ]
            if existing_acct['is_system']:
                badge_list.append(('System Account', "destructive"))
            ui.badges(
                badge_list=badge_list, 
                class_name="flex gap-2", 
                key="badges2"
            )
        
        acct_name = st.text_input(
            label='🏦 Acct Name',
            value="" if edit_mode == 'Add' else existing_acct['acct_name'],
            type='default', 
            placeholder="account name here", 
        )
        
        dds_currency = DropdownSelect.from_enum(
            CurType,
            include_null=False
        )
        
        if edit_mode == 'Add':
            if has_currency:
                cur_type_option = st.selectbox(
                    label='💲 Currency',
                    options=dds_currency.options,
                    key='cur_type_select',
                    index=0,
                )
        
            parent_acct_chart_option = st.selectbox(
                label='🔗 Attached to Chart',
                options=dds_charts.options,
                key='attach_chart_select',
                index=0,
            )
        else:
            if has_currency:
                cur_type_option = st.selectbox(
                    label='💲 Currency',
                    options=dds_currency.options,
                    key='cur_type_select2',
                    index=dds_currency.get_idx_from_id(existing_acct['currency']),
                )
        
            parent_acct_chart_option = st.selectbox(
                label='🔗 Attached to Chart',
                options=dds_charts.options,
                key='attach_chart_select2',
                index=dds_charts.get_idx_from_id(existing_acct['chart']['chart_id']),
            )
        
        parent_acct_chart_id = dds_charts.get_id(parent_acct_chart_option)
        if has_currency:
            currency: CurType = dds_currency.get_id(cur_type_option)
        else:
            currency = None

        if edit_mode == 'Add':
            # add button
            st.button(
                label='Add Account',
                on_click=add_account,
                kwargs=dict(
                    acct_name=acct_name,
                    acct_type=acct_type.value,
                    currency=currency.value if has_currency else None,
                    chart_id=parent_acct_chart_id,
                ),
                key='add_acount'
            )
            
        else:
            # update and remove button
            btn_cols = st.columns([1, 1, 5])
            with btn_cols[0]:
                st.button(
                    label='Update',
                    type='secondary',
                    on_click=update_account,
                    kwargs=dict(
                        acct_id=existing_acct_id,
                        acct_name=acct_name,
                        acct_type=acct_type.value,
                        currency=currency.value if has_currency else None,
                        chart_id=parent_acct_chart_id,
                    ),
                    key='update_acount'
                )
                    
            with btn_cols[1]:
                st.button(
                    label='Delete',
                    type='primary',
                    on_click=delete_account,
                    kwargs=dict(
                        acct_id=existing_acct_id,
                    ),
                    key='delete_acount',
                    disabled=existing_acct['is_system']
                )
                
    else:
        st.warning("No account found under this chart!", icon='🙊')