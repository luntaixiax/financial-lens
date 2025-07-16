from datetime import date
from typing import Any
from fastapi import APIRouter, Depends
from src.app.model.enums import AcctType
from src.app.service.reporting import ReportingService
from src.web.dependency.service import get_reporting_service

router = APIRouter(prefix="/reporting", tags=["reporting"])
    
@router.get("/balance_sheet_tree")
def get_balance_sheet_tree(
    rep_dt: date,
    reporting_service: ReportingService = Depends(get_reporting_service)
) -> dict[AcctType, dict]:
    return reporting_service.get_balance_sheet_tree(rep_dt)

@router.get("/income_statment_tree")
def get_income_statment_tree(
    start_dt: date,
    end_dt: date,
    reporting_service: ReportingService = Depends(get_reporting_service)
) -> dict[AcctType, dict]:
    return reporting_service.get_income_statment_tree(start_dt, end_dt)