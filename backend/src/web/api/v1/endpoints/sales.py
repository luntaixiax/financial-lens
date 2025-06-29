import base64
from datetime import date, datetime
from pathlib import Path
from typing import Any, Tuple
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.app.service.misc import SettingService
from src.app.model.payment import Payment, _PaymentBrief
from src.app.model.entity import Address, Contact, Customer, Supplier
from src.app.model.enums import CurType, ItemType, UnitType
from src.app.model.journal import Journal
from src.app.model.invoice import _InvoiceBalance, InvoiceItem, Item, Invoice, _InvoiceBrief
from src.app.service.sales import SalesService
from src.app.service.entity import EntityService

router = APIRouter(prefix="/sales", tags=["sales"])

@router.post("/invoice/validate")
def validate_sales(invoice: Invoice) -> Invoice:
    return SalesService._validate_invoice(invoice)

@router.get(
    "/invoice/trial_journal",
    description='use to generate journal during new sales invoice creation'
)
def create_journal_from_new_sales_invoice(invoice: Invoice) -> Journal:
    return SalesService.create_journal_from_invoice(invoice)

@router.get(
    "/invoice/get/{invoice_id}",
    description='get existing sales invoice and journal from database'
)
def get_sales_invoice_journal(invoice_id: str) -> Tuple[Invoice, Journal]:
    return SalesService.get_invoice_journal(invoice_id=invoice_id)

@router.post("/invoice/list")
def list_sales_invoice(
    limit: int = 50,
    offset: int = 0,
    invoice_ids: list[str] | None = None,
    invoice_nums: list[str] | None = None,
    customer_ids: list[str] | None = None,
    customer_names: list[str] | None = None,
    is_business: bool | None = None,
    min_dt: date = date(1970, 1, 1), 
    max_dt: date = date(2099, 12, 31), 
    subject_keyword: str = '',
    currency: CurType | None = None,
    min_amount: float = -999999999,
    max_amount: float = 999999999,
    num_invoice_items: int | None = None
) -> list[_InvoiceBrief]:
    return SalesService.list_invoice(
        limit=limit,
        offset=offset,
        invoice_ids=invoice_ids,
        invoice_nums=invoice_nums,
        customer_ids=customer_ids,
        customer_names=customer_names,
        is_business=is_business,
        min_dt=min_dt,
        max_dt=max_dt,
        subject_keyword=subject_keyword,
        currency=currency,
        min_amount=min_amount,
        max_amount=max_amount,
        num_invoice_items=num_invoice_items
    )

@router.post("/invoice/add")
def add_sales_invoice(invoice: Invoice):
    SalesService.add_invoice(invoice=invoice)
    
@router.put("/invoice/update")
def update_sales_invoice(invoice: Invoice):
    SalesService.update_invoice(invoice=invoice)
    
@router.delete("/invoice/delete/{invoice_id}")
def delete_sales_invoice(invoice_id: str):
    SalesService.delete_invoice(invoice_id=invoice_id)

BASE_PATH = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "templates"))


@router.get("/invoice/preview", response_class=HTMLResponse)
def preview_sales_invoice(request: Request, invoice_id: str):
    invoice, journal = SalesService.get_invoice_journal(invoice_id)
    # bill to will always be customer
    bill_to = EntityService.get_customer(invoice.entity_id)
    
    # bill_from company
    # bill from will always be supplier
    bill_from_name, bill_from_contact = SettingService.get_company()
    bill_from = Supplier(
        supplier_name = bill_from_name,
        is_business=True,
        bill_contact=bill_from_contact,
        ship_same_as_bill=True
    )
    css_path = SettingService.get_static_server_path()
    
    data = {
        'css_path': css_path,
        'logo': base64.b64encode(bytes(SettingService.get_logo().content, encoding='latin-1')).decode("latin-1"),
        'bill_from': bill_from.model_dump(mode='python'),
        'bill_to': bill_to.model_dump(mode='python'),
        'invoice': invoice.model_dump(mode='python')
    }

    return TEMPLATES.TemplateResponse(
        "invoice.html", 
        {"request": request} | data
    )

    
@router.post("/payment/validate")
def validate_payment(payment: Payment) -> Payment:
    return SalesService._validate_payment(payment)
    
@router.get(
    "/payment/trial_journal",
    description='use to generate journal during new sales payment creation'
)
def create_journal_from_new_sales_payment(payment: Payment) -> Journal:
    return SalesService.create_journal_from_payment(payment)

@router.get(
    "/payment/get/{payment_id}",
    description='get existing sales payment and journal from database'
)
def get_sales_payment_journal(payment_id: str) -> Tuple[Payment, Journal]:
    return SalesService.get_payment_journal(payment_id=payment_id)

@router.post("/payment/list")
def list_sales_payment(
    limit: int = 50,
    offset: int = 0,
    payment_ids: list[str] | None = None,
    payment_nums: list[str] | None = None,
    payment_acct_id: str | None = None,
    payment_acct_name: str | None = None,
    invoice_ids: list[str] | None = None,
    invoice_nums: list[str] | None = None,
    currency: CurType | None = None,
    min_dt: date = date(1970, 1, 1), 
    max_dt: date = date(2099, 12, 31),
    min_amount: float = -999999999,
    max_amount: float = 999999999,
    num_invoices: int | None = None
) -> list[_PaymentBrief]:
    return SalesService.list_payment(
        limit=limit,
        offset=offset,
        payment_ids=payment_ids,
        payment_nums=payment_nums,
        payment_acct_id=payment_acct_id,
        payment_acct_name=payment_acct_name,
        invoice_ids=invoice_ids,
        invoice_nums=invoice_nums,
        currency=currency,
        min_dt=min_dt,
        max_dt=max_dt,
        min_amount=min_amount,
        max_amount=max_amount,
        num_invoices=num_invoices
    )
    

@router.post("/payment/add")
def add_sales_payment(payment: Payment):
    SalesService.add_payment(payment=payment)
    
@router.put("/payment/update")
def update_sales_payment(payment: Payment):
    SalesService.update_payment(payment=payment)
    
@router.delete("/payment/delete/{payment_id}")
def delete_sales_payment(payment_id: str):
    SalesService.delete_payment(payment_id=payment_id)
    
@router.get("/invoice/{invoice_id}/get_balance")
def get_sales_invoice_balance(invoice_id: str, bal_dt: date) -> _InvoiceBalance:
    return SalesService.get_invoice_balance(
        invoice_id=invoice_id,
        bal_dt=bal_dt
    )

@router.get("/invoice/get_balance_by_entity/{entity_id}")
def get_sales_invoices_balance_by_entity(entity_id: str, bal_dt: date) -> list[_InvoiceBalance]:
    return SalesService.get_invoices_balance_by_entity(
        entity_id=entity_id,
        bal_dt=bal_dt
    )