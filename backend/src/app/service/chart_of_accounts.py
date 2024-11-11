import logging
from src.app.model.const import SystemAcctNumber, SystemChartOfAcctNumber
from src.app.utils.tools import get_base_cur
from src.app.dao.accounts import acctDao, chartOfAcctDao
from src.app.model.accounts import Account, Chart, ChartNode
from src.app.model.enums import AcctType
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, NotExistError

class AcctService:
    
    @classmethod
    def init(cls):
        # step 1. create basic chart
        # asset chart of accounts
        total_asset = ChartNode(
            Chart(
                chart_id=SystemChartOfAcctNumber.TOTAL_ASSET, 
                name='1000 - Total Asset',
                acct_type=AcctType.AST
            )
        )
        current_asset = ChartNode(
            Chart(
                chart_id=SystemChartOfAcctNumber.CUR_ASSET,
                name='1100 - Current Asset',
                acct_type=AcctType.AST
            ), 
            parent = total_asset
        )
        bank_asset = ChartNode(
            Chart(
                chart_id=SystemChartOfAcctNumber.BANK_ASSET,
                name='1110 - Bank Asset',
                acct_type=AcctType.AST
            ), 
            parent = current_asset
        )
        noncurrent_asset = ChartNode(
            Chart(
                chart_id=SystemChartOfAcctNumber.NONCUR_ASSET,
                name='1200 - Non-Current Asset',
                acct_type=AcctType.AST
            ), 
            parent = total_asset
        )
        # liability chart of accounts
        total_liability = ChartNode(
            Chart(
                chart_id=SystemChartOfAcctNumber.TOTAL_LIB, 
                name='2000 - Total Liability',
                acct_type=AcctType.LIB
            )
        )
        current_liability = ChartNode(
            Chart(
                chart_id=SystemChartOfAcctNumber.CUR_LIB, 
                name='2100 - Current Liability',
                acct_type=AcctType.LIB
            ), 
            parent = total_liability
        )
        bank_liability = ChartNode(
            Chart(
                chart_id=SystemChartOfAcctNumber.BANK_LIB, 
                name='2110 - Bank Liability',
                acct_type=AcctType.LIB
            ), 
            parent = current_liability
        )
        noncurrent_liability = ChartNode(
            Chart(
                chart_id=SystemChartOfAcctNumber.NONCUR_LIB, 
                name='2200 - Non-Current Liability',
                acct_type=AcctType.LIB
            ), 
            parent = total_liability
        )
        # equity chart of accounts
        total_equity = ChartNode(
            Chart(
                chart_id=SystemChartOfAcctNumber.TOTAL_EQU, 
                name='3000 - Total Equity',
                acct_type=AcctType.EQU
            )
        )
        # income chart of accounts
        total_income = ChartNode(
            Chart(
                chart_id=SystemChartOfAcctNumber.TOTAL_INC, 
                name='4000 - Total Income',
                acct_type=AcctType.INC
            )
        )
        # expense chart of accounts
        total_expense = ChartNode(
            Chart(
                chart_id=SystemChartOfAcctNumber.TOTAL_EXP, 
                name='5000 - Total Expense',
                acct_type=AcctType.EXP
            )
        )
    
        cls.save_chart_of_accounts(total_asset)
        cls.save_chart_of_accounts(total_liability)
        cls.save_chart_of_accounts(total_equity)
        cls.save_chart_of_accounts(total_income)
        cls.save_chart_of_accounts(total_expense)
        
        
        # create system accounts (tax, AR/AP, etc.)
        input_tax = Account(
            acct_id=SystemAcctNumber.INPUT_TAX,
            acct_name="Input Tax",
            acct_type=AcctType.AST,
            currency=get_base_cur(),
            chart=noncurrent_asset.chart
        )
        output_tax = Account(
            acct_id=SystemAcctNumber.OUTPUT_TAX,
            acct_name="Output Tax",
            acct_type=AcctType.LIB,
            currency=get_base_cur(),
            chart=noncurrent_liability.chart
        )
        ar = Account(
            acct_id=SystemAcctNumber.ACCT_RECEIV,
            acct_name="Account Receivable",
            acct_type=AcctType.AST,
            currency=get_base_cur(),
            chart=current_asset.chart
        )
        ap = Account(
            acct_id=SystemAcctNumber.ACCT_PAYAB,
            acct_name="Account Payable",
            acct_type=AcctType.LIB,
            currency=get_base_cur(),
            chart=current_liability.chart
        )
        cc = Account(
            acct_id=SystemAcctNumber.CONTR_CAP,
            acct_name="Contributed Capital",
            acct_type=AcctType.EQU,
            currency=get_base_cur(),
            chart=total_equity.chart
        )
        api = Account(
            acct_id=SystemAcctNumber.ADD_PAID_IN,
            acct_name="Additional Paid In",
            acct_type=AcctType.EQU,
            currency=get_base_cur(),
            chart=total_equity.chart
        )
        re = Account(
            acct_id=SystemAcctNumber.RETAIN_EARN,
            acct_name="Retained Earnings",
            acct_type=AcctType.EQU,
            currency=get_base_cur(),
            chart=total_equity.chart
        )
        oci = Account(
            acct_id=SystemAcctNumber.OTH_COMP_INC,
            acct_name="Other Comprehensive Income",
            acct_type=AcctType.EQU,
            currency=get_base_cur(),
            chart=total_equity.chart
        )
        sc = Account(
            acct_id=SystemAcctNumber.SHIP_CHARGE,
            acct_name="Shipping Charge",
            acct_type=AcctType.INC,
            chart=total_income.chart
        )
        disc = Account(
            acct_id=SystemAcctNumber.DISCOUNT,
            acct_name="Discount",
            acct_type=AcctType.INC,
            chart=total_income.chart
        )
        
        cls.add_account(input_tax)
        cls.add_account(output_tax)
        cls.add_account(ar)
        cls.add_account(ap)
        cls.add_account(cc)
        cls.add_account(api)
        cls.add_account(re)
        cls.add_account(oci)
        cls.add_account(sc)
        cls.add_account(disc)
        
    @classmethod
    def get_coa(cls, acct_type: AcctType) -> ChartNode:
        # TODO: error handling: not exist
        return chartOfAcctDao.load(acct_type=acct_type)
        
    @classmethod
    def save_chart_of_accounts(cls, node: ChartNode):
        chartOfAcctDao.save(node)
    
    @classmethod
    def add_account(cls, acct: Account, ignore_exist: bool = False):
        try:
            acctDao.add(acct)
        except AlreadyExistError as e:
            if not ignore_exist:
                raise AlreadyExistError(e)
            
    @classmethod
    def get_account(cls, acct_id: str) -> Account:
        return acctDao.get(acct_id)
    
    @classmethod
    def delete_account(cls, acct_id: str, ignore_nonexist: bool = False):
        try:
            acctDao.remove(acct_id)
        except NotExistError as e:
            if not ignore_nonexist:
                raise NotExistError(e)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(e)
            