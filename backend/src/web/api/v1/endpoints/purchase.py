import base64
from datetime import date, datetime
from pathlib import Path
from typing import Any, Tuple
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.app.service.misc import SettingService
from src.app.model.payment import _PaymentBrief, Payment
from src.app.model.entity import Address, Contact, Customer, Supplier
from src.app.model.enums import CurType, ItemType, UnitType
from src.app.model.journal import Journal
from src.app.model.invoice import _InvoiceBalance, InvoiceItem, Item, Invoice, _InvoiceBrief
from src.app.service.purchase import PurchaseService
from src.app.service.entity import EntityService
from src.web.dependency.service import get_purchase_service, get_setting_service, get_entity_service

router = APIRouter(prefix="/purchase", tags=["purchase"])

@router.post("/invoice/validate")
def validate_purchase(
    invoice: Invoice,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> Invoice:
    return purchase_service._validate_invoice(invoice)

@router.get(
    "/invoice/trial_journal",
    description='use to generate journal during new purchase invoice creation'
)
def create_journal_from_new_purchase_invoice(
    invoice: Invoice,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> Journal:
    return purchase_service.create_journal_from_invoice(invoice)

@router.get(
    "/invoice/get/{invoice_id}",
    description='get existing purchase invoice and journal from database'
)
def get_purchase_invoice_journal(
    invoice_id: str,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> Tuple[Invoice, Journal]:
    return purchase_service.get_invoice_journal(invoice_id=invoice_id)

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
    num_invoice_items: int | None = None,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> list[_InvoiceBrief]:
    return purchase_service.list_invoice(
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
def add_purchase_invoice(
    invoice: Invoice,
    purchase_service: PurchaseService = Depends(get_purchase_service)
):
    purchase_service.add_invoice(invoice=invoice)
    
@router.put("/invoice/update")
def update_purchase_invoice(
    invoice: Invoice,
    purchase_service: PurchaseService = Depends(get_purchase_service)
):
    purchase_service.update_invoice(invoice=invoice)
    
@router.delete("/invoice/delete/{invoice_id}")
def delete_purchase_invoice(
    invoice_id: str,
    purchase_service: PurchaseService = Depends(get_purchase_service)
):
    purchase_service.delete_invoice(invoice_id=invoice_id)

BASE_PATH = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "templates"))


@router.get("/invoice/preview", response_class=HTMLResponse)
def preview_purchase_invoice(
    request: Request,
    invoice_id: str,
    purchase_service: PurchaseService = Depends(get_purchase_service),
    setting_service: SettingService = Depends(get_setting_service),
    entity_service: EntityService = Depends(get_entity_service)
):
    invoice, journal = purchase_service.get_invoice_journal(invoice_id)
    # bill from will always be supplier
    bill_from = entity_service.get_supplier(supplier_id=invoice.entity_id)
    
    # bill_from company
    bill_to_name, bill_to_contact = setting_service.get_company()
    # bill to will always be customer
    bill_to = Customer(
        customer_name = bill_to_name,
        is_business=True,
        bill_contact=bill_to_contact,
        ship_same_as_bill=True,
        ship_contact=None
    )
    
    css_path = setting_service.get_static_server_path()
    
    data = {
        'css_path': css_path,
        'logo': base64.b64encode(
            bytes(
                setting_service.get_logo().content, 
                encoding='latin-1'
            )
        ).decode("latin-1"),
        'bill_from': bill_from.model_dump(mode='python'),
        'bill_to': bill_to.model_dump(mode='python'),
        'invoice': invoice.model_dump(mode='python')
    }

    return TEMPLATES.TemplateResponse(
        "invoice.html", 
        {"request": request} | data
    )

    
@router.post("/payment/validate")
def validate_payment(
    payment: Payment,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> Payment:
    return purchase_service._validate_payment(payment)
    
@router.get(
    "/payment/trial_journal",
    description='use to generate journal during new purchase payment creation'
)
def create_journal_from_new_purchase_payment(
    payment: Payment,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> Journal:
    return purchase_service.create_journal_from_payment(payment)

@router.get(
    "/payment/get/{payment_id}",
    description='get existing purchase payment and journal from database'
)
def get_purchase_payment_journal(
    payment_id: str,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> Tuple[Payment, Journal]:
    return purchase_service.get_payment_journal(payment_id=payment_id)

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
    num_invoices: int | None = None,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> list[_PaymentBrief]:
    return purchase_service.list_payment(
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
def add_purchase_payment(
    payment: Payment,
    purchase_service: PurchaseService = Depends(get_purchase_service)
):
    purchase_service.add_payment(payment=payment)
    
@router.put("/payment/update")
def update_purchase_payment(
    payment: Payment,
    purchase_service: PurchaseService = Depends(get_purchase_service)
):
    purchase_service.update_payment(payment=payment)
    
@router.delete("/payment/delete/{payment_id}")
def delete_purchase_payment(
    payment_id: str,
    purchase_service: PurchaseService = Depends(get_purchase_service)
):
    purchase_service.delete_payment(payment_id=payment_id)
    
@router.get("/invoice/{invoice_id}/get_balance")
def get_purchase_invoice_balance(
    invoice_id: str, 
    bal_dt: date,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> _InvoiceBalance:
    return purchase_service.get_invoice_balance(
        invoice_id=invoice_id,
        bal_dt=bal_dt
    )
    
@router.get("/invoice/get_balance_by_entity/{entity_id}")
def get_purchase_invoices_balance_by_entity(
    entity_id: str, 
    bal_dt: date,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> list[_InvoiceBalance]:
    return purchase_service.get_invoices_balance_by_entity(
        entity_id=entity_id,
        bal_dt=bal_dt
    )