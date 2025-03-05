from datetime import date
from functools import wraps
from typing import Any, Tuple
import uuid
from utils.exceptions import AlreadyExistError, NotExistError, FKNotExistError, \
    FKNoDeleteUpdateError, OpNotPermittedError, NotMatchWithSystemError, UnprocessableEntityError
from utils.base import get_req, plain_get_req, post_req, delete_req, put_req
import streamlit_shadcn_ui as ui
import streamlit as st

def message_box(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            r = f(*args, **kwargs)
        except (AlreadyExistError, NotExistError, FKNotExistError, FKNoDeleteUpdateError, 
                OpNotPermittedError, NotMatchWithSystemError, UnprocessableEntityError) as e:
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

@st.cache_data
@message_box
def list_item(entity_type: int) -> list[dict]:
    return get_req(
        prefix='item',
        endpoint='list',
        params={
            "entity_type": entity_type
        }
    )

@st.cache_data
@message_box
def get_item(item_id: str) -> dict:
    return get_req(
        prefix='item',
        endpoint=f'get/{item_id}',
    )

@message_box
def delete_item(item_id: str):
    delete_req(
        prefix='item',
        endpoint=f'delete/{item_id}',
    )
    get_item.clear()
    list_item.clear()

@message_box
def add_item(name: str, item_type: int, entity_type: int, unit: int, 
             unit_price: float, currency: int, default_acct_id: str):
    post_req(
        prefix='item',
        endpoint='add',
        data={
            "name": name,
            "item_type": item_type,
            "entity_type": entity_type,
            "unit": unit,
            "unit_price": unit_price,
            "currency": currency,
            "default_acct_id": default_acct_id,
        }
    )
    get_item.clear()
    list_item.clear()
    
@message_box
def update_item(item_id: str, name: str, item_type: int, entity_type: int, unit: int, 
             unit_price: float, currency: int, default_acct_id: str):
    put_req(
        prefix='item',
        endpoint='update',
        data={
            "item_id": item_id,
            "name": name,
            "item_type": item_type,
            "entity_type": entity_type,
            "unit": unit,
            "unit_price": unit_price,
            "currency": currency,
            "default_acct_id": default_acct_id,
        }
    )
    get_item.clear()
    list_item.clear()


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

@st.cache_data
@message_box
def tree_charts(acct_type: int) -> dict[str, Any]:
    return get_req(
        prefix='accounts',
        endpoint=f'chart/tree',
        params={
            'acct_type': acct_type
        }
    )

@st.cache_data
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
    tree_charts.clear()
    list_charts.clear()
    list_accounts_by_chart.clear()

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
    tree_charts.clear()
    list_charts.clear()
    list_accounts_by_chart.clear()

@message_box
def delete_chart(chart_id: str):
    delete_req(
        prefix='accounts',
        endpoint=f'chart/delete/{chart_id}'
    )
    tree_charts.clear()
    list_charts.clear()
    list_accounts_by_chart.clear()

@st.cache_data
@message_box
def list_accounts_by_chart(chart_id: str) -> list[dict]:
    return get_req(
        prefix='accounts',
        endpoint=f'account/list/{chart_id}',
    )

@st.cache_data  
@message_box
def get_account(acct_id: str) -> dict:
    return get_req(
        prefix='accounts',
        endpoint=f'account/get/{acct_id}',
    )

@st.cache_data
@message_box
def get_accounts_by_type(acct_type: int) -> list[dict]:
    accts = []
    charts = list_charts(acct_type)
    for chart in charts:
        accts.extend(list_accounts_by_chart(chart['chart_id']))
    return accts

@message_box
def get_all_accounts() -> list[dict]:
    accts = []
    for acct_type in (1, 2, 3, 4, 5):
        accts.extend(get_accounts_by_type(acct_type))
    return accts
    
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
    get_account.clear()
    get_accounts_by_type.clear()
    list_accounts_by_chart.clear()
    list_journal.clear()
    get_journal.clear()
    list_entry_by_acct.clear()
    
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
    get_account.clear()
    list_accounts_by_chart.clear()
    get_accounts_by_type.clear()
    list_journal.clear()
    get_journal.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()
    
@message_box
def delete_account(acct_id: str):
    delete_req(
        prefix='accounts',
        endpoint=f'account/delete/{acct_id}'
    )
    get_account.clear()
    list_accounts_by_chart.clear()
    get_accounts_by_type.clear()
    list_journal.clear()
    get_journal.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()

@st.cache_data
@message_box
def list_journal(
    limit: int = 50,
    offset: int = 0, 
    jrn_ids: list[str] | None = None,
    jrn_src: int | None = None, 
    min_dt: date = date(1970, 1, 1), 
    max_dt: date = date(2099, 12, 31), 
    acct_ids: list[str] | None = None,
    acct_names: list[str] | None = None,
    note_keyword: str = '', 
    min_amount: float = -999999999,
    max_amount: float = 999999999,
    num_entries: int | None = None
) -> Tuple[list[dict], int]:
    return post_req(
        prefix='journal',
        endpoint='list',
        params={
            'limit': limit,
            'offset': offset, 
            'jrn_src': jrn_src, 
            'min_dt': min_dt.strftime('%Y-%m-%d'), 
            'max_dt': max_dt.strftime('%Y-%m-%d'), 
            'note_keyword': note_keyword, 
            'min_amount': min_amount,
            'max_amount': max_amount,
            'num_entries': num_entries
        },
        data={
            'jrn_ids': jrn_ids,
            'acct_ids': acct_ids,
            'acct_names': acct_names,
        }
    )
    
@st.cache_data
@message_box
def stat_journal_by_src() -> dict[int, Tuple[int, float]]:
    # [(jrn_src, count, sum amount)]
    result = get_req(
        prefix='journal',
        endpoint=f'stat/stat_by_src',
    )
    return dict(
        map(
            lambda r: (r[0], (r[1], r[2])),
            result
        )
    )

@st.cache_data
@message_box
def get_journal(journal_id: str) -> dict:
    return get_req(
        prefix='journal',
        endpoint=f'get/{journal_id}',
    )

@message_box
def delete_journal(journal_id: str):
    delete_req(
        prefix='journal',
        endpoint=f'delete/{journal_id}'
    )
    stat_journal_by_src.clear()
    list_journal.clear()
    get_journal.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()

@message_box
def add_journal(jrn_date: date, jrn_src: int, entries: list[dict], note: str | None):
    converted_entries = []
    for e in entries:
        # convert acct_id to acct
        acct = get_req(
            prefix='accounts',
            endpoint=f"account/get/{e['acct_id']}",
        )
        acct.pop('is_system')
        e['acct'] =acct
        #e.pop('acct_id')
        # for balance sheet account, convert cur_incexp to None
        if acct['acct_type'] in (1, 2, 3):
            # balance sheet items
            e['cur_incexp'] = None
    
        converted_entries.append(e)
    
    post_req(
        prefix='journal',
        endpoint='add',
        data={
            'jrn_date': jrn_date.strftime('%Y-%m-%d'),
            'entries': converted_entries,
            'jrn_src': jrn_src,
            'note': note
        }
    )
    list_journal.clear()
    stat_journal_by_src.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()
    
@message_box
def update_journal(jrn_id: str, jrn_date: date, jrn_src: int, entries: list[dict], note: str | None):
    converted_entries = []
    for e in entries:
        # convert acct_id to acct
        acct = get_req(
            prefix='accounts',
            endpoint=f"account/get/{e['acct_id']}",
        )
        acct.pop('is_system')
        e['acct'] =acct
        #e.pop('acct_id')
        # for balance sheet account, convert cur_incexp to None
        if acct['acct_type'] in (1, 2, 3):
            # balance sheet items
            e['cur_incexp'] = None
    
        converted_entries.append(e)
    
    put_req(
        prefix='journal',
        endpoint='update',
        data={
            'journal_id': jrn_id,
            'jrn_date': jrn_date.strftime('%Y-%m-%d'),
            'entries': converted_entries,
            'jrn_src': jrn_src,
            'note': note
        }
    )
    stat_journal_by_src.clear()
    list_journal.clear()
    get_journal.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()
    
@st.cache_data
@message_box
def get_base_currency() -> int:
    return get_req(
        prefix='misc',
        endpoint='fx/get_base_cur'
    )

@st.cache_data
@message_box
def get_fx(src_currency: int, tgt_currency: int, cur_dt: date) -> float:
    return get_req(
        prefix='misc',
        endpoint='fx/get_rate',
        params={
            'src_currency': src_currency,
            'tgt_currency': tgt_currency,
            'cur_dt': cur_dt.strftime('%Y-%m-%d'), 
        }
    )
    
@st.cache_data
@message_box
def convert_to_base(amount: float, src_currency: int, cur_dt: date) -> float:
    return get_req(
        prefix='misc',
        endpoint='fx/convert_to_base',
        params={
            'amount': amount,
            'src_currency': src_currency,
            'cur_dt': cur_dt.strftime('%Y-%m-%d'), 
        }
    )

@st.cache_data
@message_box
def get_blsh_balance(acct_id: str, report_dt: date) -> dict:
    return get_req(
        prefix='journal',
        endpoint=f'summary/blsh_balance/get/{acct_id}',
        params={
            'report_dt': report_dt.strftime('%Y-%m-%d'),
        }
    )

@st.cache_data
@message_box
def get_incexp_flow(acct_id: str, start_dt: date, end_dt: date) -> dict:
    return get_req(
        prefix='journal',
        endpoint=f'summary/incexp_flow/get/{acct_id}',
        params={
            'start_dt': start_dt.strftime('%Y-%m-%d'),
            'end_dt': end_dt.strftime('%Y-%m-%d'),
        }
    )
    
@st.cache_data
@message_box
def list_entry_by_acct(acct_id: str) -> list[dict]:
    return get_req(
        prefix='journal',
        endpoint=f'entry/list/{acct_id}',
    )

@st.cache_data
@message_box
def get_default_tax_rate() -> float:
    return get_req(
        prefix='misc',
        endpoint='settings/get_default_tax_rate',
    )

@st.cache_data
@message_box
def list_sales_invoice(
    limit: int = 9999,
    offset: int = 0,
    invoice_ids: list[str] | None = None,
    invoice_nums: list[str] | None = None,
    customer_ids: list[str] | None = None,
    customer_names: list[str] | None = None,
    is_business: bool | None = None,
    min_dt: date = date(1970, 1, 1), 
    max_dt: date = date(2099, 12, 31), 
    subject_keyword: str = '',
    currency: int | None = None,
    min_amount: float = -999999999,
    max_amount: float = 999999999,
    num_invoice_items: int | None = None
) -> list[dict]:
    return post_req(
        prefix='sales',
        endpoint='invoice/list',
        params={
            'limit': limit,
            'offset': offset, 
            'is_business': is_business, 
            'min_dt': min_dt.strftime('%Y-%m-%d'), 
            'max_dt': max_dt.strftime('%Y-%m-%d'), 
            'subject_keyword': subject_keyword, 
            'currency': currency,
            'min_amount': min_amount,
            'max_amount': max_amount,
            'num_invoice_items': num_invoice_items
        },
        data={
            'invoice_ids': invoice_ids,
            'invoice_nums': invoice_nums,
            'customer_ids': customer_ids,
            'customer_names': customer_names,
            
        }
    )

@st.cache_data
@message_box
def get_sales_invoice_journal(invoice_id: str) -> Tuple[dict, dict]:
    return get_req(
        prefix='sales',
        endpoint=f'invoice/get/{invoice_id}',
    )

@message_box
def validate_sales(invoice: dict) -> dict:
    return post_req(
        prefix='sales',
        endpoint='invoice/validate',
        data=invoice
    )

@message_box
def create_journal_from_new_sales_invoice(invoice: dict) -> dict:
    return get_req(
        prefix='sales',
        endpoint='invoice/trial_journal',
        data=invoice
    )

@message_box
def add_sales_invoice(invoice: dict):
    post_req(
        prefix='sales',
        endpoint='invoice/add',
        data=invoice
    )
    

    list_sales_invoice.clear()
    list_journal.clear()
    stat_journal_by_src.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()

@message_box
def update_sales_invoice(invoice: dict):
    put_req(
        prefix='sales',
        endpoint='invoice/update',
        data=invoice
    )

    list_sales_invoice.clear()
    get_sales_invoice_journal.clear()
    list_journal.clear()
    stat_journal_by_src.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()
    preview_sales_invoice.clear()
    get_sales_invoice_balance.clear()

@message_box
def delete_sales_invoice(invoice_id: str):
    delete_req(
        prefix='sales',
        endpoint=f'invoice/delete/{invoice_id}'
    )
    list_sales_invoice.clear()
    get_sales_invoice_journal.clear()
    list_journal.clear()
    stat_journal_by_src.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()
    preview_sales_invoice.clear()
    get_sales_invoice_balance.clear()

@st.cache_data
@message_box
def preview_sales_invoice(invoice_id: str) -> str:
    return plain_get_req(
        prefix='sales',
        endpoint='invoice/preview',
        params={'invoice_id': invoice_id}
    )

@st.cache_data
@message_box
def list_sales_payment(
    limit: int = 9999,
    offset: int = 0,
    payment_ids: list[str] | None = None,
    payment_nums: list[str] | None = None,
    payment_acct_id: str | None = None,
    payment_acct_name: str | None = None,
    invoice_ids: list[str] | None = None,
    invoice_nums: list[str] | None = None,
    currency: int | None = None,
    min_dt: date = date(1970, 1, 1), 
    max_dt: date = date(2099, 12, 31),
    min_amount: float = -999999999,
    max_amount: float = 999999999,
    num_invoices: int | None = None
) -> list[dict]:
    return post_req(
        prefix='sales',
        endpoint='payment/list',
        params={
            'limit': limit,
            'offset': offset, 
            'payment_acct_id': payment_acct_id, 
            'payment_acct_name': payment_acct_name,
            'min_dt': min_dt.strftime('%Y-%m-%d'), 
            'max_dt': max_dt.strftime('%Y-%m-%d'), 
            'currency': currency,
            'min_amount': min_amount,
            'max_amount': max_amount,
            'num_invoices': num_invoices
        },
        data={
            'payment_ids': payment_ids,
            'payment_nums': payment_nums,
            'invoice_ids': invoice_ids,
            'invoice_nums': invoice_nums,            
        }
    )
    
@st.cache_data
@message_box
def get_sales_payment_journal(payment_id: str) -> Tuple[dict, dict]:
    return get_req(
        prefix='sales',
        endpoint=f'payment/get/{payment_id}',
    )

@st.cache_data
@message_box
def get_sales_invoice_balance(invoice_id: str, bal_dt: date) -> dict:
    return get_req(
        prefix='sales',
        endpoint=f'invoice/{invoice_id}/get_balance',
        params={
            'bal_dt': bal_dt.strftime('%Y-%m-%d')
        }
    )
    
@st.cache_data
@message_box
def get_psales_invoices_balance_by_entity(entity_id: str, bal_dt: date) -> dict:
    return get_req(
        prefix='sales',
        endpoint=f'invoice/get_balance_by_entity/{entity_id}',
        params={
            'bal_dt': bal_dt.strftime('%Y-%m-%d')
        }
    )

@message_box
def validate_sales_payment(payment: dict) -> dict:
    return post_req(
        prefix='sales',
        endpoint='payment/validate',
        data=payment
    )

@message_box
def create_journal_from_new_sales_payment(payment: dict) -> dict:
    return get_req(
        prefix='sales',
        endpoint='payment/trial_journal',
        data=payment
    )
    
@message_box
def add_sales_payment(payment: dict):
    post_req(
        prefix='sales',
        endpoint='payment/add',
        data=payment
    )

    list_sales_payment.clear()
    list_journal.clear()
    stat_journal_by_src.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()
    get_sales_invoice_balance.clear()
    get_psales_invoices_balance_by_entity.clear()
    
@message_box
def update_sales_payment(payment: dict):
    put_req(
        prefix='sales',
        endpoint='payment/update',
        data=payment
    )

    list_sales_payment.clear()
    get_sales_payment_journal.clear()
    list_journal.clear()
    stat_journal_by_src.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()
    get_sales_invoice_balance.clear()
    get_psales_invoices_balance_by_entity.clear()

@message_box
def delete_sales_payment(payment_id: str):
    delete_req(
        prefix='sales',
        endpoint=f'payment/delete/{payment_id}'
    )
    list_sales_payment.clear()
    get_sales_payment_journal.clear()
    list_journal.clear()
    stat_journal_by_src.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()
    get_sales_invoice_balance.clear()
    get_psales_invoices_balance_by_entity.clear()

@message_box
def validate_expense(expense: dict) -> dict:
    return post_req(
        prefix='expense',
        endpoint='validate',
        data=expense
    )

@message_box
def create_journal_from_new_expense(expense: dict) -> dict:
    return get_req(
        prefix='expense',
        endpoint='trial_journal',
        data=expense
    )

@st.cache_data
@message_box
def get_expense_journal(expense_id: str) -> Tuple[dict, dict]:
    return get_req(
        prefix='expense',
        endpoint=f"get_expense_journal/{expense_id}",
    )

@st.cache_data
@message_box
def list_expense(
    limit: int = 50,
    offset: int = 0,
    expense_ids: list[str] | None = None,
    min_dt: date = date(1970, 1, 1), 
    max_dt: date = date(2099, 12, 31), 
    currency: int | None = None,
    payment_acct_id: str | None = None,
    payment_acct_name: str | None = None,
    expense_acct_ids: list[str] | None = None,
    expense_acct_names: list[str] | None = None,
    min_amount: float = -999999999,
    max_amount: float = 999999999,
    has_receipt: bool | None = None
) -> Tuple[list[dict], int]:
    return post_req(
        prefix='expense',
        endpoint='list',
        params={
            'limit': limit,
            'offset': offset, 
            'payment_acct_id': payment_acct_id, 
            'payment_acct_name': payment_acct_name,
            'min_dt': min_dt.strftime('%Y-%m-%d'), 
            'max_dt': max_dt.strftime('%Y-%m-%d'), 
            'currency': currency,
            'min_amount': min_amount,
            'max_amount': max_amount,
            'has_receipt': has_receipt
        },
        data={
            'expense_ids': expense_ids,
            'expense_acct_ids': expense_acct_ids,
            'expense_acct_names': expense_acct_names,          
        }
    )

@message_box
def add_expense(expense: dict, files: list[str]):
    #save the files
    if len(files) > 0:
        file_ids = upload_file(files)
        expense['receipts'] = file_ids
        
    post_req(
        prefix='expense',
        endpoint='add',
        data=expense
    )
    list_expense.clear()
    list_journal.clear()
    stat_journal_by_src.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()

@message_box
def update_expense(expense: dict, files: list[str]):
    #save the files
    if len(files) > 0:
        file_ids = upload_file(files)
        
        existing_receipts = expense['receipts'] or []
        existing_receipts.extend(file_ids)
        existing_receipts = list(set(existing_receipts))
        expense['receipts'] = existing_receipts
        
    put_req(
        prefix='expense',
        endpoint='update',
        data=expense
    )
    get_expense_journal.clear()
    list_expense.clear()
    list_journal.clear()
    stat_journal_by_src.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()
    
    
@message_box
def delete_expense(expense_id: str):
    delete_req(
        prefix='expense',
        endpoint=f'delete/{expense_id}'
    )
    get_expense_journal.clear()
    list_expense.clear()
    list_journal.clear()
    stat_journal_by_src.clear()
    get_blsh_balance.clear()
    get_incexp_flow.clear()
    list_entry_by_acct.clear()

@message_box
def upload_file(files: list[Tuple[str, bytes]]) -> list[str]:
    return post_req(
        prefix='misc',
        endpoint='upload_file',
        files=files
    )

@message_box
def delete_file(file_id: str):
    delete_req(
        prefix='misc',
        endpoint=f'delete_file/{file_id}'
    )

@message_box
def get_file(file_id: str) -> dict:
    f = get_req(
        prefix='misc',
        endpoint=f"get_file/{file_id}",
    )
    # convert file from string to bytes
    return {
        'file_id': f['file_id'],
        'filename': f['filename'],
        'content': f['content'].encode('latin-1'),
        'filehash': f['filehash']
    }