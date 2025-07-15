from typing import Any
from fastapi import APIRouter, Depends
from src.app.model.enums import AcctType
from src.app.service.acct import AcctService
from src.app.model.accounts import Account, Chart
from src.web.dependency.service import get_acct_service

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.post("/chart/add")
def add_chart(
    chart: Chart, 
    parent_chart_id: str, 
    acct_service: AcctService = Depends(get_acct_service)
):
    acct_service.add_chart(
        child_chart=chart,
        parent_chart_id=parent_chart_id
    )
    
@router.put("/chart/update")
def update_chart(
    chart: Chart, 
    acct_service: AcctService = Depends(get_acct_service)
):
    acct_service.update_chart(
        chart=chart
    )
    
@router.put("/chart/move")
def move_chart(
    chart_id: str, 
    new_parent_chart_id: str, 
    acct_service: AcctService = Depends(get_acct_service)
):
    acct_service.move_chart(
        chart_id=chart_id,
        new_parent_chart_id=new_parent_chart_id
    )
    
@router.delete("/chart/delete/{chart_id}")
def delete_chart(
    chart_id: str, 
    acct_service: AcctService = Depends(get_acct_service)
):
    acct_service.delete_chart(chart_id=chart_id)
    
@router.get("/chart/get/{chart_id}")
def get_chart(
    chart_id: str, 
    acct_service: AcctService = Depends(get_acct_service)
) -> Chart:
    return acct_service.get_chart(chart_id=chart_id)

@router.get("/chart/{chart_id}/get_parent")
def get_parent_chart(
    chart_id: str, 
    acct_service: AcctService = Depends(get_acct_service)
) -> Chart | None:
    return acct_service.get_parent_chart(chart_id=chart_id)

@router.get("/chart/list")
def list_charts(
    acct_type: AcctType, 
    acct_service: AcctService = Depends(get_acct_service)
) -> list[Chart]:
    return acct_service.get_charts(acct_type=acct_type)

@router.get("/chart/tree")
def tree_charts(
    acct_type: AcctType, 
    acct_service: AcctService = Depends(get_acct_service)
) -> dict[str, Any]:
    return acct_service.export_coa(acct_type=acct_type, simple=True)

@router.get("/account/get/{acct_id}")
def get_account(
    acct_id: str,
    acct_service: AcctService = Depends(get_acct_service)
) -> Account:
    return acct_service.get_account(acct_id=acct_id)

@router.get("/account/list/{chart_id}")
def list_accounts_by_chart(
    chart_id: str, 
    acct_service: AcctService = Depends(get_acct_service)
) -> list[Account]:
    return acct_service.get_accounts_by_chart(
        chart=acct_service.get_chart(chart_id=chart_id)
    )
    
@router.post("/account/add")
def add_account(
    acct: Account, 
    acct_service: AcctService = Depends(get_acct_service)
):
    acct_service.add_account(
        acct=acct,
        ignore_exist=False
    )
    
@router.put("/account/update")
def update_account(
    acct: Account, 
    acct_service: AcctService = Depends(get_acct_service)
):
    acct_service.update_account(
        acct=acct,
        ignore_nonexist=False
    )

@router.put("/account/upsert")
def upsert_account(
    acct: Account, 
    acct_service: AcctService = Depends(get_acct_service)
):
    acct_service.upsert_account(acct=acct)
    
    
@router.delete("/account/delete/{acct_id}")
def delete_account(
    acct_id: str, 
    acct_service: AcctService = Depends(get_acct_service)
):
    acct_service.delete_account(
        acct_id=acct_id,
        ignore_nonexist=False,
        restrictive=True
    )