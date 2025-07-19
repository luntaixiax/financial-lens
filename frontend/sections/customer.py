from functools import wraps
import streamlit as st
import streamlit_shadcn_ui as ui
from utils.tools import DropdownSelect
from utils.apis import list_contacts, get_contact, list_customer, add_customer, \
    update_customer, get_customer, delete_customer, get_comp_contact, get_logo
from utils.apis import cookie_manager

st.set_page_config(layout="centered")
if cookie_manager.get("authenticated") != True:
    st.switch_page('sections/login.py')
access_token=cookie_manager.get("access_token")

with st.sidebar:
    comp_name, _ = get_comp_contact(access_token=access_token)
    
    st.markdown(f"Hello, :rainbow[**{comp_name}**]")
    st.logo(get_logo(), size='large')

st.subheader('Manage Customer')

tabs = st.tabs(['Customers', 'Add/Edit Customer'])
with tabs[0]:
    customers = list_customer(access_token=access_token)
    
    card_cols = st.columns(2)
    with card_cols[0]:
        ui.metric_card(
            title="# Customers", 
            content=len(customers), 
            description="registered in system", 
            key="card1"
        )
    with card_cols[1]:
        ui.metric_card(
            title="# Business Customers", 
            content=len(list(1 for cust in customers if cust['is_business'])), 
            description="registered in system", 
            key="card2"
        )
    
    if len(customers) > 0:
        st.data_editor(
            data=customers, 
            use_container_width=True,
            hide_index=True,
            disabled=True
        )
    else:
        st.warning("No Customer found", icon='🥵')

with tabs[1]:
    dds_entities = DropdownSelect(
        briefs=customers,
        include_null=False,
        id_key='cust_id',
        display_keys=['cust_id', 'customer_name']
    )
    
    edit_cols = st.columns([1, 3])
    with edit_cols[0]:
        edit_mode = st.radio(
            label='Edit Mode',
            options=['Add', 'Edit'],
            #default='Add',
            #selection_mode ='single',
            horizontal=True,
            index=1 if len(customers) > 0 else 0,
            disabled=not(len(customers) > 0)
        )
    
    if edit_mode == 'Edit':
        with edit_cols[1]:
            edit_entity = st.selectbox(
                label='👇 Select Customer',
                options=dds_entities.options,
                index=0
            )
        # selected something, will load it from database first
        existing_entity_id = dds_entities.get_id(edit_entity)
        existing_entity = get_customer(existing_entity_id, access_token=access_token)
    
    st.divider()
    
    if edit_mode == 'Edit':
        ui.badges(
            badge_list=[("Customer ID", "default"), (existing_entity_id, "secondary")], 
            class_name="flex gap-2", 
            key="badges1"
        )
    
    cname = st.text_input(
        label="👤 Customer Name",
        value="" if edit_mode == 'Add' else existing_entity['customer_name'],
        type='default', 
        placeholder="customer name here", 
        key="cname"
    )
    
    cust_cols = st.columns(2, border=True)
    with cust_cols[0]:
        if edit_mode == 'Add':
            # need if...else... bc of bug
            is_business = st.toggle(
                label='Is Business 💼',
                value=True,
                key='isbus1'
            )
        else:
            is_business = st.toggle(
                label='Is Business',
                value=existing_entity['is_business'],
                key='isbus2'
            )

    contacts = list_contacts(access_token=access_token)
    dds_contacts = DropdownSelect(
        briefs=contacts,
        include_null=False,
        id_key='contact_id',
        display_keys=['contact_id', 'name']
    )

    with cust_cols[0]:
        bill_contact_option = st.selectbox(
            label='📧 Billing Contact',
            options=dds_contacts.options,
            index=0 if edit_mode == 'Add' else dds_contacts.get_idx_from_id(
                existing_entity['bill_contact']['contact_id']
            ),
            disabled=not(len(contacts) > 0)
        )
        if len(contacts) > 0:
            with st.popover(label='Expand to See Billing Contact'):
                bill_contact_id = dds_contacts.get_id(bill_contact_option)
                st.json(get_contact(bill_contact_id, access_token=access_token))
        else:
            st.warning("No Contact setup yet, please go to Contact page to set it up first", icon='🥵')
    
    with cust_cols[1]:
        if edit_mode == 'Add':
            # need if...else... bc of bug
            ship_same_as_bill = st.toggle(
                label='Ship Address Same as Billing Address',
                value=True,
                key='shipsame1'
            )
        else:
            ship_same_as_bill = st.toggle(
                label='Ship Address Same as Billing Address',
                value=existing_entity['ship_same_as_bill'],
                key='shipsame2'
            )
    
    if not ship_same_as_bill:
        with cust_cols[1]:
            if edit_mode == 'Add':
                ship_contact_option = st.selectbox(
                    label='📧 Shipping Contact',
                    options=dds_contacts.options,
                    index=0,
                    key='sel1'
                )
            elif edit_mode == 'Edit':
                ship_contact_option = st.selectbox(
                    label='📧 Shipping Contact',
                    options=dds_contacts.options,
                    index=dds_contacts.get_idx_from_id(
                        existing_entity['ship_contact']['contact_id']
                    ),
                    key='sel2'
                )
                
            if len(contacts) > 0:
                with st.popover(label='Expand to See Shipping Contact'):
                    ship_contact_id = dds_contacts.get_id(ship_contact_option)
                    st.json(get_contact(ship_contact_id, access_token=access_token))
            else:
                st.warning("No Contact setup yet, please go to Contact page to set it up first", icon='🥵')
    else:
        ship_contact_id = None
        
    
    if edit_mode == 'Add':
        # add button
        if len(contacts) > 0:
            st.button(
                label='Add Customer',
                on_click=add_customer,
                kwargs=dict(
                    customer_name=cname, is_business=is_business, 
                    bill_contact_id=bill_contact_id, 
                    ship_same_as_bill=ship_same_as_bill, 
                    ship_contact_id=ship_contact_id,
                    access_token=access_token
                )
            )
    else:
        # update and remove button
        btn_cols = st.columns([1, 1, 5])
        with btn_cols[0]:
            st.button(
                label='Update',
                type='secondary',
                on_click=update_customer,
                kwargs=dict(
                    cust_id=existing_entity_id,
                    customer_name=cname, is_business=is_business, 
                    bill_contact_id=bill_contact_id, 
                    ship_same_as_bill=ship_same_as_bill, 
                    ship_contact_id=ship_contact_id,
                    access_token=access_token
                )
            )
        with btn_cols[1]:
            st.button(
                label='Delete',
                type='primary',
                on_click=delete_customer,
                kwargs=dict(
                    cust_id=existing_entity_id,
                    access_token=access_token
                )
            )