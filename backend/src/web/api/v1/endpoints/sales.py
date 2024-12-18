from datetime import date
from typing import Any
from fastapi import APIRouter
from src.app.model.enums import CurType
from src.app.model.journal import Journal
from src.app.model.invoice import Item, Invoice, _InvoiceBrief
from src.app.service.sales import SalesService

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

@router.get(
    "invoice/trial_journal",
    description='use to generate journal during new invoice creation'
)
def create_journal_from_new_invoice(invoice: Invoice) -> Journal:
    return SalesService.create_journal_from_invoice(invoice)

@router.get(
    "invoice/get_invoice_journal/{invoice_id}",
    description='get existing invoice and journal from database'
)
def get_invoice_journal(invoice_id: str) -> Journal:
    return SalesService.get_invoice_journal(invoice_id=invoice_id)

@router.get("invoice/list")
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
    

    
