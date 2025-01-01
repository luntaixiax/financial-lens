from functools import wraps
import streamlit as st
import streamlit_shadcn_ui as ui
from utils.tools import DropdownSelect
from utils.apis import country_list, city_list, list_contacts, get_contact, add_contact, update_contact, delete_contact


tabs = st.tabs(['Contacts', 'Add/Edit Contact'])
with tabs[0]:
    entities = list_contacts()

    ui.metric_card(
        title="# Contacts", 
        content=len(entities), 
        description="registered in system", 
        key="card1"
    )
    st.data_editor(
        data=entities, 
        use_container_width=True,
        hide_index=True,
        disabled=True
    )

with tabs[1]:
    dds_entities = DropdownSelect(
        briefs=entities,
        include_null=False,
        id_key='contact_id',
        display_keys=['contact_id', 'name']
    )
    
    edit_cols = st.columns([1, 3])
    with edit_cols[0]:
        edit_mode = st.radio(
            label='Edit Mode',
            options=['Add', 'Edit'],
            #default='Add',
            #selection_mode ='single',
            horizontal=True,
        )
    
    if edit_mode == 'Edit':
        with edit_cols[1]:
            edit_entity = st.selectbox(
                label='Select Contact',
                options=dds_entities.options,
                index=0
            )
        # selected something, will load it from database first
        existing_entity_id = dds_entities.get_id(edit_entity)
        existing_entity = get_contact(existing_entity_id)
    
    st.divider()
    
    bname = st.text_input(
        label="👤 Name",
        value="" if edit_mode == 'Add' else existing_entity['name'],
        type='default', 
        placeholder="contact name here", 
        key="bname"
    )
    
    contact_cols = st.columns(2)
    with contact_cols[0]:
        bemail = st.text_input(
            label="✉️ Email",
            value="" if edit_mode == 'Add' else existing_entity['email'],
            type='default', 
            placeholder="email here", 
            key="bemail"
        )
    with contact_cols[1]:
        bphone = st.text_input(
            label="📞 Phone", 
            value="" if edit_mode == 'Add' else existing_entity['phone'],
            type='default', 
            placeholder="phone here", 
            key="bphone"
        )
    with st.popover(label='Address', icon='📍', use_container_width=True):
        baddress1 = st.text_input(
            label="🛣️ Address1",
            value="" if edit_mode == 'Add' else existing_entity['address']['address1'], 
            type='default', 
            placeholder="1 Yong St E", 
            key="badress1"
        )
        baddress2 = st.text_input(
            label="🛣️ Address2", 
            value="" if edit_mode == 'Add' else existing_entity['address']['address2'], 
            type='default', 
            placeholder="(optional)", 
            key="badress2"
        )
        bsuite_no = st.text_input(
            label="🚪 Suite Number", 
            value="" if edit_mode == 'Add' else existing_entity['address']['suite_no'], 
            type='default', 
            placeholder="502", 
            key="bsuitenum"
        )
        _country_list = country_list()
        bcountry = st.selectbox(
            label="🌎 Country", 
            options=_country_list,
            index=0 if edit_mode == 'Add' else _country_list.index(existing_entity['address']['country']),
            key="bcountry"
        )
        _city_list = city_list(bcountry)
        bcity = st.selectbox(
            label="🌇 City", 
            options=_city_list,
            index=0 if edit_mode == 'Add' else _city_list.index(existing_entity['address']['city']),
            key="bcity"
        )
        bstate = st.text_input(
            label="State/Province", 
            value="" if edit_mode == 'Add' else existing_entity['address']['state'], 
            type='default', 
            placeholder="Ontario",
            key="bstate"
        )
        bpostal = st.text_input(
            label="📦 Postal Code", 
            value="" if edit_mode == 'Add' else existing_entity['address']['postal_code'], 
            type='default', 
            placeholder="ABC123", 
            key="bpostal"
        )
    
    if edit_mode == 'Add':
        # add button
        st.button(
            label='Add Contact',
            on_click=add_contact,
            kwargs=dict(
                name=bname, email=bemail, phone=bphone, 
                address1=baddress1, address2=baddress2, suite_no=bsuite_no, 
                city=bcity, state=bstate, country=bcountry, postal_code=bpostal
            )
        )
    else:
        # update and remove button
        btn_cols = st.columns([1, 1, 5])
        with btn_cols[0]:
            st.button(
                label='Update',
                type='secondary',
                on_click=update_contact,
                kwargs=dict(
                    contact_id=existing_entity_id, name=bname, email=bemail, phone=bphone, 
                    address1=baddress1, address2=baddress2, suite_no=bsuite_no, 
                    city=bcity, state=bstate, country=bcountry, postal_code=bpostal
                )
            )
        with btn_cols[1]:
            st.button(
                label='Delete',
                type='primary',
                on_click=delete_contact,
                kwargs=dict(
                    contact_id=existing_entity_id
                )
            )