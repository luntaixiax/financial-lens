import math
import time
import io
import uuid
import streamlit as st
import streamlit_shadcn_ui as ui
from utils.enums import CurType
from utils.tools import DropdownSelect
from utils.apis import set_logo, get_logo, list_country, list_state, list_city, \
    upsert_comp_contact, get_comp_contact, is_setup, get_base_currency, \
    get_default_tax_rate, set_default_tax_rate, get_par_share_price, set_par_share_price, initiate
from utils.apis import cookie_manager
st.set_page_config(layout="centered")

if cookie_manager.get("authenticated") != True:
    st.switch_page('sections/login.py')
access_token=cookie_manager.get("access_token")


st.subheader("Your Company LOGO")
logo_cols = st.columns([1, 4])
with logo_cols[1]:
    logo = st.file_uploader(
        label='Your Company LOGO',
        accept_multiple_files=False,
    )
    if logo is not None:
        bytes_logo = io.BufferedReader(logo)
        set_logo(bytes_logo, access_token=access_token)

with logo_cols[0]:
    st.image(get_logo(access_token=access_token))
    
st.subheader("Your Company Contact")
comp_name, existing_entity = get_comp_contact(access_token=access_token)
    
contact_cols = st.columns(2)
with contact_cols[0]:
    cname = st.text_input(
        label="🏢 Company Name",
        value="" if comp_name is None else comp_name,
        type='default', 
        placeholder="company name here", 
        key="cname"
    )
with contact_cols[1]:
    bname = st.text_input(
        label="👤 Contact Name",
        value="" if existing_entity is None else existing_entity['name'],
        type='default', 
        placeholder="contact name here", 
        key="bname"
    )

with contact_cols[0]:
    bemail = st.text_input(
        label="✉️ Email",
        value="" if existing_entity is None else existing_entity['email'],
        type='default', 
        placeholder="email here", 
        key="bemail"
    )
with contact_cols[1]:
    bphone = st.text_input(
        label="📞 Phone", 
        value="" if existing_entity is None else existing_entity['phone'],
        type='default', 
        placeholder="phone here", 
        key="bphone"
    )
with st.popover(label='Address', icon='📍', use_container_width=True):
    baddress1 = st.text_input(
        label="🛣️ Address1",
        value="" if existing_entity is None else existing_entity['address']['address1'], 
        type='default', 
        placeholder="1 Yong St E", 
        key="badress1"
    )
    baddress2 = st.text_input(
        label="🛣️ Address2", 
        value="" if existing_entity is None else existing_entity['address']['address2'], 
        type='default', 
        placeholder="(optional)", 
        key="badress2"
    )
    bsuite_no = st.text_input(
        label="🚪 Suite Number", 
        value="" if existing_entity is None else existing_entity['address']['suite_no'], 
        type='default', 
        placeholder="502", 
        key="bsuitenum"
    )
    
    # add country
    countries = list_country()
    dds_countries = DropdownSelect(
        briefs=countries,
        include_null=False,
        id_key='iso2',
        display_keys=['country']
    )
    if existing_entity is None:
        bcountry = st.selectbox(
            label="🌎 Country", 
            options=dds_countries.options,
            index=0,
            key="bcountry"
        )
    else:
        bcountry = st.selectbox(
            label="🌎 Country", 
            options=dds_countries.options,
            index=dds_countries.get_idx_from_option(existing_entity['address']['country']),
            key="bcountry2"
        )
    # add state
    states = list_state(
        country_iso2=dds_countries.get_id(bcountry),
    )
    dds_states = DropdownSelect(
        briefs=states,
        include_null=False,
        id_key='iso2',
        display_keys=['state']
    )
    if existing_entity is None:
        bstate = st.selectbox(
            label="🌎 State", 
            options=dds_states.options,
            index=0,
            key="bstate"
        )
    else:
        bstate = st.selectbox(
            label="🌎 State", 
            options=dds_states.options,
            index=dds_states.get_idx_from_option(existing_entity['address']['state']),
            key="bstate2"
        )
    # add city
    cities = list_city(
        country_iso2=dds_countries.get_id(bcountry),
        state_iso2=dds_states.get_id(bstate)
    )
    if existing_entity is None:
        bcity = st.selectbox(
            label="🌇 City", 
            options=cities,
            index=0,
            key="bcity"
        )
    else:
        bcity = st.selectbox(
            label="🌇 City", 
            options=cities,
            index=cities.index(existing_entity['address']['city']),
            key="bcity2"
        )
    
    bpostal = st.text_input(
        label="📦 Postal Code", 
        value="" if existing_entity is None else existing_entity['address']['postal_code'], 
        type='default', 
        placeholder="ABC123", 
        key="bpostal"
    )
    
st.button(
    label='Update Contact',
    on_click=upsert_comp_contact,
    kwargs=dict(
        company_name=cname, name=bname, email=bemail, phone=bphone, 
        address1=baddress1, address2=baddress2, suite_no=bsuite_no, 
        city=bcity, state=bstate, country=bcountry, postal_code=bpostal,
        access_token=access_token
    ),
    key='btn_contact'
)


st.subheader("Your Accounting Default Settings")

is_set = is_setup(access_token=access_token)

current_base_cur = get_base_currency(ignore_error=True, access_token=access_token) or CurType.USD.value
current_default_tax_rate = get_default_tax_rate(ignore_error=True, access_token=access_token) or 0.13
current_par_share_price = get_par_share_price(ignore_error=True, access_token=access_token) or 0.01

st.toggle(
    label = 'Is Setup Already?',
    value = is_set,
    disabled=True
)
st.warning("Only **default tax rate** can be changed. Once setup, you cannot change **base currency**!", icon='🚨')


acct_cols = st.columns(2)
with acct_cols[0]:
    dds_currency = DropdownSelect.from_enum(
        CurType,
        include_null=False
    )
    
    base_cur = st.selectbox(
        label='Base Currency',
        options=dds_currency.options,
        disabled=is_set,
        index=dds_currency.get_idx_from_id(current_base_cur)
    )
    
with acct_cols[1]:
    default_tax_rate = st.number_input(
        label='Default Tax Rate (%)',
        min_value=0.0,
        max_value=100.0,
        step=0.1,
        value=current_default_tax_rate * 100
    )

with acct_cols[0]:
    par_share_price = st.number_input(
        label=f'Par Shar Price ({CurType[base_cur].name})',
        min_value=0.0,
        step=0.01,
        value=current_par_share_price,
        disabled=is_set,
    )
    
if is_set:
    st.button(
        label='Update Default Settings',
        key='btn_update_default',
        on_click=set_default_tax_rate,
        kwargs=dict(
            default_tax_rate=default_tax_rate / 100,
            access_token=access_token
        )
    )
else:
    st.button(
        label='Initiate',
        key='btn_initiate',
        on_click=initiate,
        kwargs=dict(
            base_cur=CurType[base_cur].value,
            default_tax_rate=default_tax_rate / 100,
            par_share_price=par_share_price,
            access_token=access_token
        )
    )