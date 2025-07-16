from datetime import date
from typing import Tuple
from fastapi import APIRouter, Depends
from src.app.model.journal import Journal
from src.app.service.shares import SharesService
from src.app.model.shares import StockIssue, StockRepurchase, Dividend
from src.web.dependency.service import get_shares_service

router = APIRouter(prefix="/shares", tags=["shares"])

@router.post("/issue/validate_issue")
def validate_issue(
    issue: StockIssue,
    shares_service: SharesService = Depends(get_shares_service)
) -> StockIssue:
    return shares_service._validate_issue(issue)
    
@router.get(
    "/issue/trial_journal",
    description='use to generate journal during new issue creation'
)
def create_journal_from_new_issue(
    issue: StockIssue,
    shares_service: SharesService = Depends(get_shares_service)
) -> Journal:
    return shares_service.create_journal_from_issue(issue)

@router.get(
    "/issue/get_issue_journal/{issue_id}",
    description='get existing issue and journal from database'
)
def get_issue_journal(
    issue_id: str,
    shares_service: SharesService = Depends(get_shares_service)
) -> Tuple[StockIssue, Journal]:
    return shares_service.get_issue_journal(issue_id=issue_id)

@router.get("/issue/list")
def list_issue(
    is_reissue: bool = False,
    shares_service: SharesService = Depends(get_shares_service)
) -> list[StockIssue]:
    return shares_service.list_issues(is_reissue)

@router.get("/issue/list_reissue_from_repur")
def list_reissue_from_repur(
    repur_id: str,
    shares_service: SharesService = Depends(get_shares_service)
) -> list[StockIssue]:
    return shares_service.list_reissue_from_repur(
        repur_id=repur_id
    )

@router.get("/issue/get_total_reissue_from_repur")
def get_total_reissue_from_repur(
    repur_id: str, 
    rep_dt: date, 
    exclu_issue_id: str | None = None,
    shares_service: SharesService = Depends(get_shares_service)
) -> float:
    return shares_service.get_total_reissue_from_repur(
        repur_id=repur_id, 
        rep_dt=rep_dt, 
        exclu_issue_id=exclu_issue_id
    )
    

@router.post("/issue/add")
def add_issue(
    issue: StockIssue,
    shares_service: SharesService = Depends(get_shares_service)
):
    shares_service.add_issue(issue=issue)
    
@router.put("/issue/update")
def update_issue(
    issue: StockIssue,
    shares_service: SharesService = Depends(get_shares_service)
):
    shares_service.update_issue(issue=issue)
    
@router.delete("/issue/delete/{issue_id}")
def delete_issue(
    issue_id: str,
    shares_service: SharesService = Depends(get_shares_service)
):
    shares_service.delete_issue(issue_id=issue_id)
    
    
@router.post("/repur/validate_repur")
def validate_repur(
    repur: StockRepurchase,
    shares_service: SharesService = Depends(get_shares_service)
) -> StockRepurchase:
    return shares_service._validate_repur(repur)
    
@router.get(
    "/repur/trial_journal",
    description='use to generate journal during new repur creation'
)
def create_journal_from_new_repur(
    repur: StockRepurchase,
    shares_service: SharesService = Depends(get_shares_service)
) -> Journal:
    return shares_service.create_journal_from_repur(repur)

@router.get(
    "/repur/get_repur_journal/{repur_id}",
    description='get existing repur and journal from database'
)
def get_repur_journal(
    repur_id: str,
    shares_service: SharesService = Depends(get_shares_service)
) -> Tuple[StockRepurchase, Journal]:
    return shares_service.get_repur_journal(repur_id=repur_id)

@router.get("/repur/list")
def list_repur(
    shares_service: SharesService = Depends(get_shares_service)
) -> list[StockRepurchase]:
    return shares_service.list_repurs()  

@router.post("/repur/add")
def add_repur(
    repur: StockRepurchase,
    shares_service: SharesService = Depends(get_shares_service)
):
    shares_service.add_repur(repur=repur)
    
@router.put("/repur/update")
def update_repur(
    repur: StockRepurchase,
    shares_service: SharesService = Depends(get_shares_service)
):
    shares_service.update_repur(repur=repur)
    
@router.delete("/repur/delete/{repur_id}")
def delete_repur(
    repur_id: str,
    shares_service: SharesService = Depends(get_shares_service)
):
    shares_service.delete_repur(repur_id=repur_id)
    

@router.post("/div/validate_div")
def validate_div(
    div: Dividend,
    shares_service: SharesService = Depends(get_shares_service)
) -> Dividend:
    return shares_service._validate_div(div)
    
@router.get(
    "/div/trial_journal",
    description='use to generate journal during new div creation'
)
def create_journal_from_new_div(
    div: Dividend,
    shares_service: SharesService = Depends(get_shares_service)
) -> Journal:
    return shares_service.create_journal_from_div(div)

@router.get(
    "/div/get_div_journal/{div_id}",
    description='get existing div and journal from database'
)
def get_div_journal(
    div_id: str,
    shares_service: SharesService = Depends(get_shares_service)
) -> Tuple[Dividend, Journal]:
    return shares_service.get_div_journal(div_id=div_id)

@router.get("/div/list")
def list_div(
    shares_service: SharesService = Depends(get_shares_service)
) -> list[Dividend]:
    return shares_service.list_divs()

@router.post("/div/add")
def add_div(
    div: Dividend,
    shares_service: SharesService = Depends(get_shares_service)
):
    shares_service.add_div(div=div)
    
@router.put("/div/update")
def update_div(
    div: Dividend,
    shares_service: SharesService = Depends(get_shares_service)
):
    shares_service.update_div(div=div)
    
@router.delete("/div/delete/{div_id}")
def delete_div(
    div_id: str,
    shares_service: SharesService = Depends(get_shares_service)
):
    shares_service.delete_div(div_id=div_id)