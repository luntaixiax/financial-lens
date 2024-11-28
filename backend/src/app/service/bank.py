
from src.app.model.exceptions import NotExistError, OpNotPermittedError
from src.app.model.const import SystemChartOfAcctNumber
from src.app.service.acct import AcctService
from src.app.model.accounts import Account, Chart
from src.app.model.bank import BankAcct
from src.app.model.enums import BankAcctType, AcctType

class BankService:
    @classmethod
    def get_acct_type_from_bank_acct(cls, bank_acct: BankAcct) -> AcctType:
        if bank_acct.bank_acct_type in (BankAcctType.CHQ, BankAcctType.SAV):
            acct_type=AcctType.AST    
        else:
            acct_type=AcctType.LIB
        return acct_type
    
    @classmethod
    def get_possible_charts_for_bank_acct(cls, bank_acct: BankAcct) -> list[Chart]:
        acct_type=cls.get_acct_type_from_bank_acct(bank_acct)
        try:
            charts = AcctService.get_charts(acct_type)
        except NotExistError as e:
            raise NotExistError(
                f"Chart of Acct Type: {acct_type} not exist for this bank account: {bank_acct}.",
                details=str(e).details
            )
        return charts
            
    
    @classmethod
    def create_acct_for_bank_acct(cls, bank_acct: BankAcct, chart: Chart) -> Account:
        if not bank_acct.is_business:
            raise OpNotPermittedError(
                f"Bank Acct {bank_acct} is not business account, cannot create Account"
            )
        
        acct_type=cls.get_acct_type_from_bank_acct(bank_acct)
            
        acct = Account(
            acct_name=bank_acct.bank_acct_name,
            acct_type=acct_type,
            currency=bank_acct.currency,
            chart=chart
        )
        return acct