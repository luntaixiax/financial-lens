
from src.app.model.const import SystemChartOfAcctNumber
from src.app.service.chart_of_accounts import AcctService
from src.app.model.accounts import Account, Chart
from src.app.model.bank import BankAcct
from src.app.model.enums import BankAcctType, AcctType

class BankService:
    
    @classmethod
    def create_acct_from_bank_acct(cls, bank_acct: BankAcct) -> Account:
        if not bank_acct.is_business:
            raise TypeError(f"Bank Acct {bank_acct} is not business account, cannot create Account")
        
        if bank_acct.bank_acct_type in (BankAcctType.CHQ, BankAcctType.SAV):
            acct_type=AcctType.AST
            chart=AcctService.get_coa(AcctType.AST).find_node_by_id(
                chart_id=SystemChartOfAcctNumber.BANK_ASSET
            ).chart
        else:
            acct_type=AcctType.LIB
            chart=AcctService.get_coa(AcctType.LIB).find_node_by_id(
                chart_id=SystemChartOfAcctNumber.BANK_LIB
            ).chart
            
        acct = Account(
            acct_name=bank_acct.bank_acct_name,
            acct_type=acct_type,
            currency=bank_acct.currency,
            chart=chart
        )
        return acct