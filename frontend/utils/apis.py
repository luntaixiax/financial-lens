from functools import wraps
from typing import Any
import uuid
from utils.exceptions import AlreadyExistError, NotExistError, FKNotExistError, \
    FKNoDeleteUpdateError, OpNotPermittedError, NotMatchWithSystemError
from utils.base import get_req, post_req, delete_req, put_req
import streamlit_shadcn_ui as ui
import streamlit as st

def message_box(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            r = f(*args, **kwargs)
        except (AlreadyExistError, NotExistError, FKNotExistError, FKNoDeleteUpdateError, 
                OpNotPermittedError, NotMatchWithSystemError) as e:
            ui.alert_dialog(
                show=True,
                title=e.message,
                description=e.details,
                confirm_label="OK",
                cancel_label=e.__class__.__name__,
                key=str(uuid.uuid1())
            )
        else:
            return r

    return decorated

@st.cache_data
def list_country() -> list[dict]:
    return get_req(
        prefix='misc',
        endpoint='geo/countries/list'
    )

@st.cache_data
def list_state(country_iso2: str) -> list[dict]:
    return get_req(
        prefix='misc',
        endpoint=f'geo/countries/{country_iso2}/state/list'
    )
    
@st.cache_data
def list_city(country_iso2: str, state_iso2: str) -> list[dict]:
    return get_req(
        prefix='misc',
        endpoint=f'geo/countries/{country_iso2}/state/{state_iso2}/city/list'
    )

@message_box
def list_contacts() -> list[dict]:
    return get_req(
        prefix='entity',
        endpoint='contact/list'
    )

@message_box  
def get_contact(contact_id: str) -> dict:
    return get_req(
        prefix='entity',
        endpoint=f'contact/get/{contact_id}'
    )

@message_box
def delete_contact(contact_id: str):
    delete_req(
        prefix='entity',
        endpoint=f'contact/delete/{contact_id}'
    )

@message_box
def add_contact(name: str, email: str, phone: str, 
                address1: str, address2: str, suite_no: str, 
                city: str, state: str, country: str, postal_code: str):
    post_req(
        prefix='entity',
        endpoint='contact/add',
        data={
            "name": name,
            "email": email,
            "phone": phone,
            "address": {
                "address1": address1,
                "address2": address2,
                "suite_no": suite_no,
                "city": city,
                "state": state,
                "country": country,
                "postal_code": postal_code
            }
        }
    )

@message_box
def update_contact(contact_id: str, name: str, email: str, phone: str, 
                address1: str, address2: str, suite_no: str, 
                city: str, state: str, country: str, postal_code: str):
    put_req(
        prefix='entity',
        endpoint='contact/update',
        data={
            "contact_id": contact_id,
            "name": name,
            "email": email,
            "phone": phone,
            "address": {
                "address1": address1,
                "address2": address2,
                "suite_no": suite_no,
                "city": city,
                "state": state,
                "country": country,
                "postal_code": postal_code
            }
        }
    )

@message_box
def list_customer() -> list[dict]:
    return get_req(
        prefix='entity',
        endpoint='customer/list'
    )
    

@message_box
def get_customer(cust_id: str) -> dict:
    return get_req(
        prefix='entity',
        endpoint=f'customer/get/{cust_id}'
    )

@message_box
def delete_customer(cust_id: str):
    delete_req(
        prefix='entity',
        endpoint=f'customer/delete/{cust_id}'
    )

@message_box
def add_customer(customer_name: str, is_business: bool, bill_contact_id: str, 
                 ship_same_as_bill: bool, ship_contact_id: str | None):
    
    bill_contact = get_req(
        prefix='entity',
        endpoint=f'contact/get/{bill_contact_id}'
    )
    if ship_contact_id is None:
        ship_contact = None
    else:
        ship_contact = get_req(
            prefix='entity',
            endpoint=f'contact/get/{ship_contact_id}'
        )
    
    post_req(
        prefix='entity',
        endpoint='customer/add',
        data={
            "customer_name": customer_name,
            "is_business": is_business,
            "bill_contact": bill_contact,
            "ship_same_as_bill": ship_same_as_bill,
            "ship_contact": ship_contact
        }
    )

@message_box
def update_customer(cust_id: str, customer_name: str, is_business: bool, bill_contact_id: str, 
                 ship_same_as_bill: bool, ship_contact_id: str | None):
    bill_contact = get_contact(bill_contact_id)
    if ship_contact_id is None:
        ship_contact = None
    else:
        ship_contact = get_contact(ship_contact_id)
        
    put_req(
        prefix='entity',
        endpoint='customer/update',
        data={
            "cust_id": cust_id,
            "customer_name": customer_name,
            "is_business": is_business,
            "bill_contact": bill_contact,
            "ship_same_as_bill": ship_same_as_bill,
            "ship_contact": ship_contact
        }
    )
    
@message_box
def list_supplier() -> list[dict]:
    return get_req(
        prefix='entity',
        endpoint='supplier/list'
    )
    

@message_box
def get_supplier(supplier_id: str) -> dict:
    return get_req(
        prefix='entity',
        endpoint=f'supplier/get/{supplier_id}'
    )

@message_box
def delete_supplier(supplier_id: str):
    delete_req(
        prefix='entity',
        endpoint=f'supplier/delete/{supplier_id}'
    )

@message_box
def add_supplier(supplier_name: str, is_business: bool, bill_contact_id: str, 
                 ship_same_as_bill: bool, ship_contact_id: str | None):
    
    bill_contact = get_contact(bill_contact_id)
    if ship_contact_id is None:
        ship_contact = None
    else:
        ship_contact = get_contact(ship_contact_id)
    
    post_req(
        prefix='entity',
        endpoint='supplier/add',
        data={
            "supplier_name": supplier_name,
            "is_business": is_business,
            "bill_contact": bill_contact,
            "ship_same_as_bill": ship_same_as_bill,
            "ship_contact": ship_contact
        }
    )

@message_box
def update_supplier(supplier_id: str, supplier_name: str, is_business: bool, bill_contact_id: str, 
                 ship_same_as_bill: bool, ship_contact_id: str | None):
    bill_contact = get_contact(bill_contact_id)
    if ship_contact_id is None:
        ship_contact = None
    else:
        ship_contact = get_contact(ship_contact_id)
        
    put_req(
        prefix='entity',
        endpoint='supplier/update',
        data={
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "is_business": is_business,
            "bill_contact": bill_contact,
            "ship_same_as_bill": ship_same_as_bill,
            "ship_contact": ship_contact
        }
    )
    
@message_box
def tree_charts(acct_type: int) -> dict[str, Any]:
    return get_req(
        prefix='accounts',
        endpoint=f'chart/tree',
        params={
            'acct_type': acct_type
        }
    )

@message_box
def list_charts(acct_type: int) -> list[dict]:
    return get_req(
        prefix='accounts',
        endpoint='chart/list',
        params={
            'acct_type': acct_type
        }
    )

@message_box
def get_chart(chart_id: str) -> dict:
    return get_req(
        prefix='accounts',
        endpoint=f'chart/get/{chart_id}',
    )
    
@message_box
def get_parent_chart(chart_id: str) -> dict:
    return get_req(
        prefix='accounts',
        endpoint=f'chart/{chart_id}/get_parent',
    )
    
@message_box
def list_accounts_by_chart(chart_id: str) -> list[dict]:
    return get_req(
        prefix='accounts',
        endpoint=f'account/list/{chart_id}',
    )

@message_box  
def add_chart(chart: dict, parent_chart_id: str):
    post_req(
        prefix='accounts',
        endpoint='chart/add',
        params={
            'parent_chart_id': parent_chart_id
        },
        data={
            "name": chart['name'],
            "acct_type": chart['acct_type'],
        }
    )

@message_box
def update_move_chart(chart: dict, parent_chart_id: str):
    # update chart
    put_req(
        prefix='accounts',
        endpoint='chart/update',
        data={
            "chart_id": chart['chart_id'],
            "name": chart['name'],
            "acct_type": chart['acct_type'],
        }
    )
    # move chart
    put_req(
        prefix='accounts',
        endpoint='chart/move',
        params={
            "chart_id": chart['chart_id'],
            "new_parent_chart_id": parent_chart_id,
        }
    )

@message_box
def delete_chart(chart_id: str):
    delete_req(
        prefix='accounts',
        endpoint=f'chart/delete/{chart_id}'
    )
    
@message_box
def list_accounts_by_chart(chart_id: str) -> list[dict]:
    return get_req(
        prefix='accounts',
        endpoint=f'account/list/{chart_id}',
    )
    
@message_box
def get_account(acct_id: str) -> dict:
    return get_req(
        prefix='accounts',
        endpoint=f'account/get/{acct_id}',
    )

@message_box
def add_account(acct_name: str, acct_type: int, currency: int, chart_id: str):
    chart = get_req(
        prefix='accounts',
        endpoint=f'chart/get/{chart_id}',
    )
    post_req(
        prefix='accounts',
        endpoint='account/add',
        data={
            "acct_name": acct_name,
            "acct_type": acct_type,
            "currency": currency,
            "chart": chart
        }
    )
    
@message_box
def update_account(acct_id: str, acct_name: str, acct_type: int, currency: int, chart_id: str):
    chart = get_req(
        prefix='accounts',
        endpoint=f'chart/get/{chart_id}',
    )
    put_req(
        prefix='accounts',
        endpoint='account/update',
        data={
            "acct_id": acct_id,
            "acct_name": acct_name,
            "acct_type": acct_type,
            "currency": currency,
            "chart": chart
        }
    )
    
@message_box
def delete_account(acct_id: str):
    delete_req(
        prefix='accounts',
        endpoint=f'account/delete/{acct_id}'
    )