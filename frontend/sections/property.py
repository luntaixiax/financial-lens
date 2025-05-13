import math
import time
import uuid
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit.components.v1 as components
from datetime import datetime, date, timedelta
from utils.apis import list_property, get_account, get_property_journal
from utils.enums import PropertyType, PropertyTransactionType, CurType
from utils.tools import DropdownSelect

st.set_page_config(layout="centered")

def reset_validate():
    #st.session_state['validated'] = False
    pass
    
def reset_page():
    reset_validate()
    if 'journal' in st.session_state:
        del st.session_state['journal']

def clear_entries_from_cache():
    # st.session_state['validated'] = False
    pass
        
def clear_entries_and_reset_page():
    clear_entries_from_cache()
    reset_page()

property_types = DropdownSelect.from_enum(
    PropertyType,
    include_null=False
)

properties = list_property()

st.subheader("Properties (Fixed Asset)")
if len(properties) > 0:
    property_display = pd.DataFrame.from_records([
        {
            'Property ID': p['property_id'],
            'Property': p['property_name'],
            'Type': PropertyType(p['property_type']).name,
            'Purchase Date': p['pur_dt'],
            'Price': f"{CurType(get_account(p['pur_acct_id'])['currency']).name} {round(p['pur_price'], 2):,.2f}",
            'Purchase Acct': get_account(p['pur_acct_id'])['acct_name']
            
        } for p in properties
    ])

    ui.table(property_display)
    
    # if there is property, show the property details and show transactions
    
    widget_cols = st.columns([1, 2])
    with widget_cols[0]:
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
        with widget_cols[1]:
            dds_property = DropdownSelect(
                briefs=properties,
                include_null=False,
                id_key='property_id',
                display_keys=['property_id', 'property_name']
            )
            edit_property = st.selectbox(
                label='👇 Select Property',
                options=dds_property.options,
                index=0
            )
            existing_property_id = dds_property.get_id(edit_property)
            existing_prop_item, existing_journal = get_property_journal(existing_property_id)
            
    st.divider()
    
    if edit_mode == 'Edit':
        ui.badges(
            badge_list=[("Property ID", "default"), (existing_property_id, "secondary")], 
            class_name="flex gap-2", 
            key="badges1"
        )
        
    property_name = st.text_input(
        label="💻 Property Name",
        value="" if edit_mode == 'Add' else existing_prop_item['property_name'],
        type='default', 
        placeholder="property name here", 
        key="pname"
    )
    if edit_mode == 'Add':
        
        property_type = st.radio(
            label = '🆎 Property Type',
            options=property_types.options,
            index=0,
            horizontal=True,
            key='radio1',
        )
    elif edit_mode == 'Edit':
        property_type = st.radio(
            label = '🆎 Property Type',
            options=property_types.options,
            index=property_types.get_idx_from_option(PropertyType(existing_prop_item['property_type']).name),
            horizontal=True,
            key='radio2',
        )
    
else:
    st.info("No properties purchased yet!", icon='😐')