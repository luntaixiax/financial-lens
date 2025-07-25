from datetime import date
from typing import Tuple
from fastapi import APIRouter, Depends
from src.app.model.invoice import GeneralInvoiceItem
from src.app.model.enums import CurType
from src.app.model.journal import Journal
from src.app.model.expense import _ExpenseBrief, _ExpenseSummaryBrief, Expense
from src.app.service.expense import ExpenseService
from src.web.dependency.service import get_expense_service

router = APIRouter(prefix="/expense", tags=["expense"])

@router.post("/validate")
def validate_expense(
    expense: Expense, 
    expense_service: ExpenseService = Depends(get_expense_service)
) -> Expense:
    return expense_service._validate_expense(expense)
    
@router.get(
    "/trial_journal",
    description='use to generate journal during new expense creation'
)
def create_journal_from_new_expense(
    expense: Expense, 
    expense_service: ExpenseService = Depends(get_expense_service)
) -> Journal:
    return expense_service.create_journal_from_expense(expense)

@router.get(
    "/get_expense_journal/{expense_id}",
    description='get existing expense and journal from database'
)
def get_expense_journal(
    expense_id: str, 
    expense_service: ExpenseService = Depends(get_expense_service)
) -> Tuple[Expense, Journal]:
    return expense_service.get_expense_journal(expense_id=expense_id)

@router.get(
    "/create_invoice_items/{expense_id}",
    description='creating general invoice items from given expense'
)
def create_general_invoice_items_from_expense(
    expense_id: str, 
    invoice_currency: CurType, 
    expense_service: ExpenseService = Depends(get_expense_service)
) -> list[GeneralInvoiceItem]:
    return expense_service.create_general_invoice_items_from_expense(
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
    has_receipt: bool | None = None,
    expense_service: ExpenseService = Depends(get_expense_service),
) -> Tuple[list[_ExpenseBrief], int]:
    return expense_service.list_expense(
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

@router.get("/summary")
def summary_expense(
    start_dt: date, 
    end_dt: date, 
    expense_service: ExpenseService = Depends(get_expense_service)
) -> list[_ExpenseSummaryBrief]:
    return expense_service.summary_expense(
        start_dt=start_dt,
        end_dt=end_dt
    )
    
@router.post("/add")
def add_expense(
    expense: Expense, 
    expense_service: ExpenseService = Depends(get_expense_service)
):
    expense_service.add_expense(expense=expense)
    
@router.post("/batch_add")
def add_expenses(
    expenses: list[Expense], 
    expense_service: ExpenseService = Depends(get_expense_service)
):
    expense_service.add_expenses(expenses=expenses)
    
@router.put("/update")
def update_expense(
    expense: Expense, 
    expense_service: ExpenseService = Depends(get_expense_service)
):
    expense_service.update_expense(expense=expense)
    
@router.delete("/delete/{expense_id}")
def delete_expense(
    expense_id: str, 
    expense_service: ExpenseService = Depends(get_expense_service)
):
    expense_service.delete_expense(expense_id=expense_id)