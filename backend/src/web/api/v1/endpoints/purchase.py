from datetime import date, datetime
from pathlib import Path
from typing import Any, Tuple
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.app.model.payment import _PaymentBrief, Payment
from src.app.utils.tools import get_company
from src.app.model.entity import Address, Contact, Customer, Supplier
from src.app.model.enums import CurType, ItemType, UnitType
from src.app.model.journal import Journal
from src.app.model.invoice import InvoiceItem, Item, Invoice, _InvoiceBrief
from src.app.service.purchase import PurchaseService
from src.app.service.entity import EntityService

router = APIRouter(prefix="/purchase", tags=["purchase"])

@router.post("/invoice/validate")
def validate_purchase(invoice: Invoice) -> Invoice:
    return PurchaseService._validate_invoice(invoice)

@router.get(
    "/invoice/trial_journal",
    description='use to generate journal during new purchase invoice creation'
)
def create_journal_from_new_purchase_invoice(invoice: Invoice) -> Journal:
    return PurchaseService.create_journal_from_invoice(invoice)

@router.get(
    "/invoice/get/{invoice_id}",
    description='get existing purchase invoice and journal from database'
)
def get_purchase_invoice_journal(invoice_id: str) -> Tuple[Invoice, Journal]:
    return PurchaseService.get_invoice_journal(invoice_id=invoice_id)

@router.post("/invoice/list")
def list_purchase_invoice(
    limit: int = 50,
    offset: int = 0,
    invoice_ids: list[str] | None = None,
    invoice_nums: list[str] | None = None,
    supplier_ids: list[str] | None = None,
    supplier_names: list[str] | None = None,
    is_business: bool | None = None,
    min_dt: date = date(1970, 1, 1), 
    max_dt: date = date(2099, 12, 31), 
    subject_keyword: str = '',
    currency: CurType | None = None,
    min_amount: float = -999999999,
    max_amount: float = 999999999,
    num_invoice_items: int | None = None
) -> list[_InvoiceBrief]:
    return PurchaseService.list_invoice(
        limit=limit,
        offset=offset,
        invoice_ids=invoice_ids,
        invoice_nums=invoice_nums,
        supplier_ids=supplier_ids,
        supplier_names=supplier_names,
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
def add_purchase_invoice(invoice: Invoice):
    PurchaseService.add_invoice(invoice=invoice)
    
@router.put("/invoice/update")
def update_purchase_invoice(invoice: Invoice):
    PurchaseService.update_invoice(invoice=invoice)
    
@router.delete("/invoice/delete/{invoice_id}")
def delete_purchase_invoice(invoice_id: str):
    PurchaseService.delete_invoice(invoice_id=invoice_id)

BASE_PATH = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "templates"))


@router.get("/invoice/preview", response_class=HTMLResponse)
def preview_purchase_invoice(request: Request, invoice_id: str):
    invoice, journal = PurchaseService.get_invoice_journal(invoice_id)
    # bill from will always be supplier
    bill_from = EntityService.get_supplier(invoice.entity_id)
    
    # bill_from company
    bill_to_company = get_company()
    # bill to will always be customer
    bill_to = Customer(
        customer_name = bill_to_company['name'],
        is_business=True,
        bill_contact=Contact.model_validate(bill_to_company['contact']),
        ship_same_as_bill=True
    )
    
    data = {
        'logo': bill_to_company['logo'],
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
    return PurchaseService._validate_payment(payment)
    
@router.get(
    "/payment/trial_journal",
    description='use to generate journal during new purchase payment creation'
)
def create_journal_from_new_purchase_payment(payment: Payment) -> Journal:
    return PurchaseService.create_journal_from_payment(payment)

@router.get(
    "/payment/get/{payment_id}",
    description='get existing purchase payment and journal from database'
)
def get_purchase_payment_journal(payment_id: str) -> Tuple[Payment, Journal]:
    return PurchaseService.get_payment_journal(payment_id=payment_id)

@router.post("/payment/list")
def list_purchase_payment(
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
    return PurchaseService.list_payment(
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
def add_purchase_payment(payment: Invoice):
    PurchaseService.add_payment(payment=payment)
    
@router.put("/payment/update")
def update_purchase_payment(payment: Invoice):
    PurchaseService.update_payment(payment=payment)
    
@router.delete("/payment/delete/{payment_id}")
def delete_purchase_payment(payment_id: str):
    PurchaseService.delete_payment(payment_id=payment_id)