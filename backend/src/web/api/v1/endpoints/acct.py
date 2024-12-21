from typing import Any
from fastapi import APIRouter
from src.app.model.enums import AcctType
from src.app.service.acct import AcctService
from src.app.model.accounts import Account, Chart

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.post("/chart/add")
def add_chart(chart: Chart, parent_chart_id: str):
    AcctService.add_chart(
        child_chart=chart,
        parent_chart_id=parent_chart_id
    )
    
@router.put("/chart/update")
def update_chart(chart: Chart):
    AcctService.update_chart(
        chart=chart
    )
    
@router.put("/chart/move")
def move_chart(chart_id: str, new_parent_chart_id: str):
    AcctService.move_chart(
        chart_id=chart_id,
        new_parent_chart_id=new_parent_chart_id
    )
    
@router.delete("/chart/delete/{chart_id}")
def delete_chart(chart_id: str):
    AcctService.delete_chart(chart_id=chart_id)
    
@router.get("/chart/get/{chart_id}")
def get_chart(chart_id: str) -> Chart:
    return AcctService.get_chart(chart_id=chart_id)

@router.get("/chart/list")
def list_charts(acct_type: AcctType) -> list[Chart]:
    return AcctService.get_charts(acct_type=acct_type)

@router.get("/chart/tree")
def tree_charts(acct_type: AcctType) -> dict[str, Any]:
    return AcctService.export_coa(acct_type=acct_type, simple=True)

@router.get("/account/get/{acct_id}")
def get_account(acct_id: str) -> Account:
    return AcctService.get_account(acct_id=acct_id)

@router.get("/account/list/{chart_id}")
def list_accounts_by_chart(chart_id: str) -> list[Account]:
    return AcctService.get_accounts_by_chart(
        chart=AcctService.get_chart(chart_id=chart_id)
    )
    
@router.post("/account/add")
def add_account(acct: Account):
    AcctService.add_account(
        acct=acct,
        ignore_exist=False
    )
    
@router.put("/account/update")
def update_account(acct: Account):
    AcctService.update_account(
        acct=acct,
        ignore_nonexist=False
    )

@router.put("/account/upsert")
def upsert_account(acct: Account):
    AcctService.upsert_account(acct=acct)
    
    
@router.delete("/account/delete/{acct_id}")
def delete_account(acct_id: str):
    AcctService.delete_account(
        acct_id=acct_id,
        ignore_nonexist=False,
        restrictive=True
    )