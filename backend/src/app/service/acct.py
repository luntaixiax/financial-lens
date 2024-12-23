import logging
from typing import Any
from anytree import PreOrderIter
from pydantic import ValidationError
from src.app.model.const import SystemAcctNumber, SystemChartOfAcctNumber
from src.app.utils.tools import get_base_cur
from src.app.dao.accounts import acctDao, chartOfAcctDao
from src.app.model.accounts import Account, Chart, ChartNode
from src.app.model.enums import AcctType, CurType
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError, NotMatchWithSystemError, OpNotPermittedError

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
    
        cls.save_coa(total_asset)
        cls.save_coa(total_liability)
        cls.save_coa(total_equity)
        cls.save_coa(total_income)
        cls.save_coa(total_expense)
        
        
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
        fx_gain = Account(
            acct_id=SystemAcctNumber.FX_GAIN,
            acct_name="FX Gain",
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
        cls.add_account(fx_gain)
        
    @classmethod
    def create_sample(cls):
        total_inc_chart = AcctService.get_chart(
            chart_id=SystemChartOfAcctNumber.TOTAL_INC
        )
        total_exp_chart = AcctService.get_chart(
            chart_id=SystemChartOfAcctNumber.TOTAL_EXP
        )
        bank_chart = AcctService.get_chart(
            chart_id=SystemChartOfAcctNumber.BANK_ASSET
        )
        noncur_chart = AcctService.get_chart(
            chart_id=SystemChartOfAcctNumber.NONCUR_ASSET
        )
        curlib_chart = AcctService.get_chart(
            chart_id=SystemChartOfAcctNumber.CUR_LIB
        )
        ncurlib_chart = AcctService.get_chart(
            chart_id=SystemChartOfAcctNumber.NONCUR_LIB
        )
        
        consult_inc = Account(
            acct_id='acct-consul',
            acct_name='Consulting Income',
            acct_type=AcctType.INC,
            chart=total_inc_chart
        )
        meal = Account(
            acct_id='acct-meal',
            acct_name='Meal Expense',
            acct_type=AcctType.EXP,
            chart=total_exp_chart
        )
        tip = Account(
            acct_id='acct-tip',
            acct_name='Tips',
            acct_type=AcctType.EXP,
            chart=total_exp_chart
        )
        rental = Account(
            acct_id='acct-rental',
            acct_name='Rental Expense',
            acct_type=AcctType.EXP,
            chart=total_exp_chart
        )
        bank = Account(
            acct_id='acct-bank',
            acct_name="Bank Acct",
            acct_type=AcctType.AST,
            currency=get_base_cur(),
            chart=bank_chart
        )
        bank_foreign = Account(
            acct_id='acct-fbank',
            acct_name="Bank Acct (JPY)",
            acct_type=AcctType.AST,
            currency=CurType.JPY,
            chart=bank_chart
        )
        fixed_asset = Account(
            acct_id='acct-fass',
            acct_name="Fixed Asset",
            acct_type=AcctType.AST,
            currency=get_base_cur(),
            chart=noncur_chart
        )
        credit = Account(
            acct_id='acct-credit',
            acct_name="Credit Acct",
            acct_type=AcctType.LIB,
            currency=get_base_cur(),
            chart=curlib_chart
        )
        shareholder_loan = Account(
            acct_id='acct-shareloan',
            acct_name="Shareholder Loan",
            acct_type=AcctType.LIB,
            currency=get_base_cur(),
            chart=ncurlib_chart
        )
        
        # add to db
        AcctService.add_account(consult_inc)
        AcctService.add_account(meal)
        AcctService.add_account(tip)
        AcctService.add_account(rental)
        AcctService.add_account(bank)
        AcctService.add_account(bank_foreign)
        AcctService.add_account(fixed_asset)
        AcctService.add_account(credit)
        AcctService.add_account(shareholder_loan)
        
    @classmethod
    def clear_sample(cls):
        for acct_type in AcctType:
            charts = AcctService.get_charts(acct_type)
            for chart in charts:
                accts = AcctService.get_accounts_by_chart(chart)
                for acct in accts:
                    AcctService.delete_account(
                        acct_id=acct.acct_id,
                        ignore_nonexist=True,
                        restrictive=False
                    )
                    
            # clean up (delete all chart of accounts)
            cls.delete_coa(acct_type)
        
    @classmethod
    def get_coa(cls, acct_type: AcctType) -> ChartNode:
        try:
            head_node = chartOfAcctDao.load(acct_type=acct_type)
        except NotExistError as e:
            raise NotExistError(
                f"Root node for {acct_type} does not exist.",
                details=e.details
            )
        return head_node
        
    @classmethod
    def save_coa(cls, node: ChartNode):
        # first need to make sure the difference (charts to be deleted) does not have account attached
        # first get already existing _charts
        _charts = cls.get_charts(node.chart.acct_type)
        # compare and find out charts to be deleted = _charts - charts
        charts = [n.chart for n in PreOrderIter(node)]
        chart_to_delete = [c for c in _charts if c not in charts]
        # make sure they dont have account attached
        for _chart in chart_to_delete:
            accts = cls.get_accounts_by_chart(_chart)
            if len(accts) > 0:
                raise FKNoDeleteUpdateError(
                    f"Chart: {_chart} contain {len(accts)} accounts, cannot be deleted"
                )
                
        try:
            chartOfAcctDao.save(node)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f'An account or chart of account belongs to the node {node}, so cannot delete it.',
                details=e.details
            )
        
    @classmethod
    def delete_coa(cls, acct_type: AcctType):
        # first need to make sure the (charts to be deleted) does not have account attached
        _charts = cls.get_charts(acct_type)
        for _chart in _charts:
            accts = cls.get_accounts_by_chart(_chart)
            if len(accts) > 0:
                raise FKNoDeleteUpdateError(
                    f"Chart: {_chart} contain {len(accts)} accounts, cannot be deleted"
                )
        
        chartOfAcctDao.remove(acct_type)
        
    @classmethod
    def export_coa(cls, acct_type: AcctType, simple: bool = False) -> dict[str, Any]:
        root = cls.get_coa(acct_type)
        return root.to_dict(simple = simple)
        
    @classmethod
    def add_chart(cls, child_chart: Chart, parent_chart_id: str):
        root = cls.get_coa(child_chart.acct_type)
        parent_node = root.find_node_by_id(parent_chart_id)
        if parent_node is None:
            raise NotExistError(
                f"Parent node not found, id = {parent_chart_id}"
            )
        child_node = ChartNode(
            chart = child_chart,
            parent = parent_node
        )
        cls.save_coa(root)
        
    @classmethod
    def delete_chart(cls, chart_id: str):
        chart = cls.get_chart(chart_id)
        # raise error if any accounts attached to this chart
        accts = cls.get_accounts_by_chart(chart)
        if len(accts) > 0:
            raise FKNoDeleteUpdateError(
                f"Cannot delete chart {chart_id} because there are {len(accts)} attached to it"
            )
        
        root = cls.get_coa(chart.acct_type)
        node = root.find_node_by_id(chart_id)
        node.parent = None # remove node = dettach from the node tree
        cls.save_coa(root)
        
    @classmethod
    def update_chart(cls, chart: Chart):
        root = cls.get_coa(chart.acct_type)
        node = root.find_node_by_id(chart.chart_id)
        node.name = chart.name
        node.chart = chart
        node.chart_id = chart.chart_id
        cls.save_coa(root)
        
    @classmethod
    def move_chart(cls, chart_id: str, new_parent_chart_id: str):
        chart = cls.get_chart(chart_id)
        root = cls.get_coa(chart.acct_type)
        new_parent_node = root.find_node_by_id(new_parent_chart_id)
        current_node = root.find_node_by_id(chart_id)
        current_node.parent = new_parent_node # set a new parent
        cls.save_coa(root)
        
        
    @classmethod
    def get_chart(cls, chart_id: str) -> Chart:
        try:
            chart = chartOfAcctDao.get_chart(chart_id=chart_id)
        except NotExistError as e:
            raise NotExistError(
                f"Chart {chart_id} not exist.",
                details=e.details
            )
        return chart
    

    @classmethod
    def get_charts(cls, acct_type: AcctType) -> list[Chart]:
        try:
            charts = chartOfAcctDao.get_charts(
                acct_type=acct_type
            )
        except NotExistError as e:
            raise NotExistError(
                f"Chart of Acct Type: {acct_type} not exist.",
                details=e.details
            )
        return charts
            
    @classmethod
    def get_account(cls, acct_id: str) -> Account:
        try:
            chart_id = acctDao.get_chart_id_by_acct(acct_id)
        except NotExistError as e:
            raise NotExistError(
                f'Acct Id: {acct_id} not exist',
                details=e.details
            )
        
        try:
            chart = chartOfAcctDao.get_chart(chart_id)
        except NotExistError as e:
            raise NotExistError(
                f'Chart Id: {chart_id} not exist',
                details=e.details
            )
        
        try:
            acct = acctDao.get(acct_id, chart)
        except NotExistError as e:
            raise NotExistError(
                f'Acct Id: {acct_id} not exist',
                details=e.details
            )
        return acct
    
    @classmethod
    def get_accounts_by_chart(cls, chart: Chart) -> list[Account]:
        try:
            accts = acctDao.get_accts_by_chart(chart)
        except NotExistError as e:
            accts = []
        return accts
            
    
    @classmethod
    def add_account(cls, acct: Account, ignore_exist: bool = False):
        # verify chart exists and not changed
        try:
            _chart = cls.get_chart(chart_id = acct.chart.chart_id)
        except NotExistError as e:
            raise FKNotExistError(
                f"Chart of account for the account added does not exist: {acct.chart}",
                details=e.details
            )
        if not _chart == acct.chart:
            raise NotMatchWithSystemError(
                message='Chart does not match with existing',
                details=f"You have {acct.chart} while existing is {_chart}"
            )
        
        try:
            acctDao.add(acct)
        except AlreadyExistError as e:
            if not ignore_exist:
                raise AlreadyExistError(
                    f'Account already exist: {acct}',
                    details=e.details
                )
        except FKNotExistError as e:
            raise FKNotExistError(
                f"Chart of account for the account added does not exist: {acct.chart}",
                details=e.details
            )
            
    @classmethod
    def update_account(cls, acct: Account, ignore_nonexist: bool = False):
        # verify chart exists and not changed
        try:
            _chart = cls.get_chart(chart_id = acct.chart.chart_id)
        except NotExistError as e:
            raise FKNotExistError(
                f"Chart: {acct.chart} of the updated account does not exist",
                details=e.details
            )
        
        if not _chart == acct.chart:
            raise NotMatchWithSystemError(
                message='Chart does not match with existing',
                details=f"You have {acct.chart} while existing is {_chart}"
            )
            
        # get acct in db first, compare some fields not be changed:
        try:
            _acct = cls.get_account(acct.acct_id)
        except NotExistError as e:
            if not ignore_nonexist:
                raise e
        
        if acct.currency != _acct.currency:
            raise NotMatchWithSystemError(
                message=f"Account currency cannot be changed",
                details=f"Before: {acct.currency}, After: {_acct.currency}"
            )
        
        # update account
        try:
            acctDao.update(acct)
        except FKNotExistError as e:
            raise FKNotExistError(
                f"Chart: {acct.chart} of the updated account does not exist",
                details=e.details
            )
            
    @classmethod
    def upsert_account(cls, acct: Account):
        try:
            cls.add_account(acct)
        except AlreadyExistError:
            try:
                cls.update_account(acct)
            except ValueError as e:
                raise e
            except FKNotExistError as e:
                raise e
        except FKNotExistError as e:
            raise e
    
    @classmethod
    def delete_account(cls, acct_id: str, ignore_nonexist: bool = False, 
                       restrictive: bool = True):
        if restrictive:
            # cannot delete system created accounts
            if acct_id in SystemAcctNumber.list():
                raise OpNotPermittedError(
                    f"Acct id {acct_id} is system account, not permitted to delete"
                )
        
        try:
            acctDao.remove(acct_id)
        except NotExistError as e:
            if not ignore_nonexist:
                raise NotExistError(
                    f'Acct Id: {acct_id} not exist',
                    details=e.details
                )
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f'There are journal entry or item relates to this account: {acct_id}, so cannot delete it.',
                details=e.details
            )