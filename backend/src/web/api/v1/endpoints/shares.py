from datetime import date
from typing import Tuple
from fastapi import APIRouter
from src.app.model.journal import Journal
from src.app.service.shares import SharesService
from src.app.model.shares import StockIssue, StockRepurchase, Dividend

router = APIRouter(prefix="/shares", tags=["shares"])

@router.post("/issue/validate_issue")
def validate_issue(issue: StockIssue) -> StockIssue:
    return SharesService._validate_issue(issue)
    
@router.get(
    "/issue/trial_journal",
    description='use to generate journal during new issue creation'
)
def create_journal_from_new_issue(issue: StockIssue) -> Journal:
    return SharesService.create_journal_from_issue(issue)

@router.get(
    "/issue/get_issue_journal/{issue_id}",
    description='get existing issue and journal from database'
)
def get_issue_journal(issue_id: str) -> Tuple[StockIssue, Journal]:
    return SharesService.get_issue_journal(issue_id=issue_id)

@router.get("/issue/list")
def list_issue(is_reissue: bool = False) -> list[StockIssue]:
    return SharesService.list_issues(is_reissue)

@router.get("/issue/list_reissue_from_repur")
def list_reissue_from_repur(repur_id: str) -> list[StockIssue]:
    return SharesService.list_reissue_from_repur(repur_id)

@router.get("/issue/get_total_reissue_from_repur")
def get_total_reissue_from_repur(repur_id: str, rep_dt: date, exclu_issue_id: str | None = None) -> float:
    return SharesService.get_total_reissue_from_repur(repur_id=repur_id, rep_dt=rep_dt, exclu_issue_id=exclu_issue_id)
    

@router.post("/issue/add")
def add_issue(issue: StockIssue):
    SharesService.add_issue(issue=issue)
    
@router.put("/issue/update")
def update_issue(issue: StockIssue):
    SharesService.update_issue(issue=issue)
    
@router.delete("/issue/delete/{issue_id}")
def delete_issue(issue_id: str):
    SharesService.delete_issue(issue_id=issue_id)
    
    
@router.post("/repur/validate_repur")
def validate_repur(repur: StockRepurchase) -> StockRepurchase:
    return SharesService._validate_repur(repur)
    
@router.get(
    "/repur/trial_journal",
    description='use to generate journal during new repur creation'
)
def create_journal_from_new_repur(repur: StockRepurchase) -> Journal:
    return SharesService.create_journal_from_repur(repur)

@router.get(
    "/repur/get_repur_journal/{repur_id}",
    description='get existing repur and journal from database'
)
def get_repur_journal(repur_id: str) -> Tuple[StockRepurchase, Journal]:
    return SharesService.get_repur_journal(repur_id=repur_id)

@router.get("/repur/list")
def list_repur() -> list[StockRepurchase]:
    return SharesService.list_repurs()

@router.post("/repur/add")
def add_repur(repur: StockRepurchase):
    SharesService.add_repur(repur=repur)
    
@router.put("/repur/update")
def update_repur(repur: StockRepurchase):
    SharesService.update_repur(repur=repur)
    
@router.delete("/repur/delete/{repur_id}")
def delete_repur(repur_id: str):
    SharesService.delete_repur(repur_id=repur_id)
    

@router.post("/div/validate_div")
def validate_div(div: Dividend) -> Dividend:
    return SharesService._validate_div(div)
    
@router.get(
    "/div/trial_journal",
    description='use to generate journal during new div creation'
)
def create_journal_from_new_div(div: Dividend) -> Journal:
    return SharesService.create_journal_from_div(div)

@router.get(
    "/div/get_div_journal/{div_id}",
    description='get existing div and journal from database'
)
def get_div_journal(div_id: str) -> Tuple[Dividend, Journal]:
    return SharesService.get_div_journal(div_id=div_id)

@router.get("/div/list")
def list_div() -> list[Dividend]:
    return SharesService.list_divs()

@router.post("/div/add")
def add_div(div: Dividend):
    SharesService.add_div(div=div)
    
@router.put("/div/update")
def update_div(div: Dividend):
    SharesService.update_div(div=div)
    
@router.delete("/div/delete/{div_id}")
def delete_div(div_id: str):
    SharesService.delete_div(div_id=div_id)