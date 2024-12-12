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