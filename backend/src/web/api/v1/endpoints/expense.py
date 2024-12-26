from datetime import date, datetime
from pathlib import Path
from typing import Any, Tuple
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.app.model.invoice import GeneralInvoiceItem
from src.app.model.enums import CurType
from src.app.model.journal import Journal
from src.app.model.expense import _ExpenseBrief, Expense
from src.app.service.expense import ExpenseService

router = APIRouter(prefix="/expense", tags=["expense"])

@router.post("/validate")
def validate_expense(expense: Expense):
    ExpenseService._validate_expense(expense)
    
@router.get(
    "/trial_journal",
    description='use to generate journal during new expense creation'
)
def create_journal_from_new_expense(expense: Expense) -> Journal:
    return ExpenseService.create_journal_from_expense(expense)

@router.get(
    "/get_expense_journal/{expense_id}",
    description='get existing expense and journal from database'
)
def get_expense_journal(expense_id: str) -> Tuple[Expense, Journal]:
    return ExpenseService.get_expense_journal(expense_id=expense_id)

@router.get(
    "/create_invoice_items/{expense_id}",
    description='creating general invoice items from given expense'
)
def create_general_invoice_items_from_expense(expense_id: str, invoice_currency: CurType) -> list[GeneralInvoiceItem]:
    return ExpenseService.create_general_invoice_items_from_expense(
        expense_id=expense_id,
        invoice_currency=invoice_currency
    )

@router.post("/list")
def list_expense(
    limit: int = 50,
    offset: int = 0,
    expense_ids: list[str] | None = None,
    min_dt: date = date(1970, 1, 1), 
    max_dt: date = date(2099, 12, 31), 
    currency: CurType | None = None,
    payment_acct_id: str | None = None,
    payment_acct_name: str | None = None,
    expense_acct_ids: list[str] | None = None,
    expense_acct_names: list[str] | None = None,
    min_amount: float = -999999999,
    max_amount: float = 999999999,
    has_receipt: bool | None = None
) -> list[_ExpenseBrief]:
    return ExpenseService.list_expense(
        limit=limit,
        offset=offset,
        expense_ids=expense_ids,
        min_dt=min_dt,
        max_dt=max_dt,
        payment_acct_id=payment_acct_id,
        payment_acct_name=payment_acct_name,
        expense_acct_ids=expense_acct_ids,
        expense_acct_names=expense_acct_names,
        currency=currency,
        min_amount=min_amount,
        max_amount=max_amount,
        has_receipt=has_receipt
    ) 
    
@router.post("/add")
def add_expense(expense: Expense):
    ExpenseService.add_expense(expense=expense)
    
@router.put("/update")
def update_expense(expense: Expense):
    ExpenseService.update_expense(expense=expense)
    
@router.delete("/delete/{expense_id}")
def delete_expense(expense_id: str):
    ExpenseService.delete_expense(expense_id=expense_id)