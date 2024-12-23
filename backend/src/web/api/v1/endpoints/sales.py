from datetime import date, datetime
from pathlib import Path
from typing import Any, Tuple
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.app.utils.tools import get_company
from src.app.model.entity import Address, Contact, Customer
from src.app.model.enums import CurType, ItemType, UnitType
from src.app.model.journal import Journal
from src.app.model.invoice import InvoiceItem, Item, Invoice, _InvoiceBrief
from src.app.service.sales import SalesService
from src.app.service.entity import EntityService

router = APIRouter(prefix="/sales", tags=["sales"])

@router.post("/item/add")
def add_item(item: Item):
    SalesService.add_item(item=item)
    
@router.put("/item/update")
def update_item(item: Item):
    SalesService.update_item(item=item)
    
@router.delete("/item/delete/{item_id}")
def delete_item(item_id: str):
    SalesService.delete_item(item_id=item_id)
    
@router.get("/item/get/{item_id}")
def get_item(item_id: str) -> Item:
    return SalesService.get_item(item_id=item_id)

@router.get("/item/list")
def list_item() -> list[Item]:
    return SalesService.list_item()

@router.post("/invoice/validate")
def validate_invoice(invoice: Invoice):
    SalesService._validate_invoice(invoice)

@router.get(
    "/invoice/trial_journal",
    description='use to generate journal during new invoice creation'
)
def create_journal_from_new_invoice(invoice: Invoice) -> Journal:
    return SalesService.create_journal_from_invoice(invoice)

@router.get(
    "/invoice/get_invoice_journal/{invoice_id}",
    description='get existing invoice and journal from database'
)
def get_invoice_journal(invoice_id: str) -> Tuple[Invoice, Journal]:
    return SalesService.get_invoice_journal(invoice_id=invoice_id)

@router.post("/invoice/list")
def list_invoice(
    limit: int = 50,
    offset: int = 0,
    invoice_ids: list[str] | None = None,
    invoice_nums: list[str] | None = None,
    customer_ids: list[str] | None = None,
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
        min_dt=min_dt,
        max_dt=max_dt,
        subject_keyword=subject_keyword,
        currency=currency,
        min_amount=min_amount,
        max_amount=max_amount,
        num_invoice_items=num_invoice_items
    )

@router.post("/invoice/add")
def add_invoice(invoice: Invoice):
    SalesService.add_invoice(invoice=invoice)
    
@router.put("/invoice/update")
def update_invoice(invoice: Invoice):
    SalesService.update_invoice(invoice=invoice)
    
@router.delete("/invoice/delete/{invoice_id}")
def delete_invoice(invoice_id: str):
    SalesService.delete_invoice(invoice_id=invoice_id)

BASE_PATH = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "templates"))


@router.get("/invoice/preview", response_class=HTMLResponse)
def preview_invoice(request: Request, invoice_id: str):
    invoice, journal = SalesService.get_invoice_journal(invoice_id)
    bill_to = EntityService.get_customer(invoice.customer_id)
    
    # bill_from company
    bill_from_company = get_company()
    bill_from = Customer(
        customer_name = bill_from_company['name'],
        is_business=True,
        bill_contact=Contact.model_validate(bill_from_company['contact']),
        ship_same_as_bill=True
    )
    
    data = {
        'logo': bill_from_company['logo'],
        'bill_from': bill_from.model_dump(mode='python'),
        'bill_to': bill_to.model_dump(mode='python'),
        'invoice': invoice.model_dump(mode='python')
    }

    return TEMPLATES.TemplateResponse(
        "invoice.html", 
        {"request": request} | data
    )

    
