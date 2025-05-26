from datetime import date
from typing import Any
from fastapi import APIRouter
from src.app.model.enums import AcctType
from src.app.service.reporting import ReportingService

router = APIRouter(prefix="/reporting", tags=["reporting"])
    
@router.get("/balance_sheet_tree")
def get_balance_sheet_tree(rep_dt: date) -> dict[AcctType, dict]:
    return ReportingService.get_balance_sheet_tree(rep_dt)

@router.get("/income_statment_tree")
def get_income_statment_tree(start_dt: date, end_dt: date) -> dict[AcctType, dict]:
    return ReportingService.get_income_statment_tree(start_dt, end_dt)