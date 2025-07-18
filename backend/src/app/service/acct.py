from typing import Any
from anytree import PreOrderIter
from src.app.model.const import SystemAcctNumber, SystemChartOfAcctNumber
from src.app.dao.accounts import acctDao, chartOfAcctDao
from src.app.model.accounts import Account, Chart, ChartNode
from src.app.model.enums import AcctType, CurType
from src.app.model.exceptions import (
    AlreadyExistError,
    FKNoDeleteUpdateError,
    FKNotExistError,
    NotExistError,
    NotMatchWithSystemError,
    OpNotPermittedError,
)
from src.app.service.misc import SettingService

class AcctService:
    
    def __init__(self, acct_dao: acctDao, chart_of_acct_dao: chartOfAcctDao, 
                 setting_service: SettingService):
        self.acct_dao = acct_dao
        self.chart_of_acct_dao = chart_of_acct_dao
        self.setting_service = setting_service
        
        
    def init(self):
        base_cur = self.setting_service.get_base_currency()
        
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
        fixed_asset = ChartNode(
            Chart(
                chart_id=SystemChartOfAcctNumber.FIXED_ASSET,
                name='1210 - Fixed Asset',
                acct_type=AcctType.AST
            ), 
            parent = noncurrent_asset
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
    
        self.save_coa(total_asset)
        self.save_coa(total_liability)
        self.save_coa(total_equity)
        self.save_coa(total_income)
        self.save_coa(total_expense)
        
        # create system accounts (tax, AR/AP, etc.)
        input_tax = Account(
            acct_id=SystemAcctNumber.INPUT_TAX,
            acct_name="Input Tax",
            acct_type=AcctType.AST,
            currency=base_cur,
            chart=noncurrent_asset.chart
        )
        output_tax = Account(
            acct_id=SystemAcctNumber.OUTPUT_TAX,
            acct_name="Output Tax",
            acct_type=AcctType.LIB,
            currency=base_cur,
            chart=noncurrent_liability.chart
        )
        ar = Account(
            acct_id=SystemAcctNumber.ACCT_RECEIV,
            acct_name="Account Receivable",
            acct_type=AcctType.AST,
            currency=base_cur,
            chart=current_asset.chart
        )
        ap = Account(
            acct_id=SystemAcctNumber.ACCT_PAYAB,
            acct_name="Account Payable",
            acct_type=AcctType.LIB,
            currency=base_cur,
            chart=current_liability.chart
        )
        cc = Account(
            acct_id=SystemAcctNumber.CONTR_CAP,
            acct_name="Contributed Capital",
            acct_type=AcctType.EQU,
            currency=base_cur,
            chart=total_equity.chart
        )
        api = Account(
            acct_id=SystemAcctNumber.ADD_PAID_IN,
            acct_name="Additional Paid In",
            acct_type=AcctType.EQU,
            currency=base_cur,
            chart=total_equity.chart
        )
        treas = Account(
            acct_id=SystemAcctNumber.TREASURY_STOCK,
            acct_name="Treasury Stock",
            acct_type=AcctType.EQU,
            currency=base_cur,
            chart=total_equity.chart
        )
        div = Account(
            acct_id=SystemAcctNumber.ACC_DIV,
            acct_name="Acc. Dividend",
            acct_type=AcctType.EQU,
            currency=base_cur,
            chart=total_equity.chart
        )
        oci = Account(
            acct_id=SystemAcctNumber.OTH_COMP_INC,
            acct_name="Other Comprehensive Income",
            acct_type=AcctType.EQU,
            currency=base_cur,
            chart=total_equity.chart
        )
        sc = Account(
            acct_id=SystemAcctNumber.SHIP_CHARGE,
            acct_name="Shipping Charge",
            acct_type=AcctType.INC,
            chart=total_income.chart,
            currency=None
        )
        disc = Account(
            acct_id=SystemAcctNumber.DISCOUNT,
            acct_name="Discount",
            acct_type=AcctType.INC,
            chart=total_income.chart,
            currency=None
        )
        fx_gain = Account(
            acct_id=SystemAcctNumber.FX_GAIN,
            acct_name="FX Gain",
            acct_type=AcctType.INC,
            chart=total_income.chart,
            currency=None
        )
        bank_fee = Account(
            acct_id=SystemAcctNumber.BANK_FEE,
            acct_name="Bank Fee",
            acct_type=AcctType.EXP,
            chart=total_expense.chart,
            currency=None
        ) # for payment entry
        ppne = Account(
            acct_id=SystemAcctNumber.PPNE,
            acct_name="PP&E",
            acct_type=AcctType.AST,
            chart=fixed_asset.chart,
            currency=base_cur,
        )
        acc_amort = Account(
            acct_id=SystemAcctNumber.ACC_ADJ,
            acct_name="Acc. PP&E Adj.",
            acct_type=AcctType.AST,
            chart=fixed_asset.chart,
            currency=base_cur,
        ) # accumulative amortization
        amort = Account(
            acct_id=SystemAcctNumber.DEPRECIATION,
            acct_name="Depreciation",
            acct_type=AcctType.EXP,
            chart=total_expense.chart,
            currency=None
        )
        appre = Account(
            acct_id=SystemAcctNumber.APPRECIATION,
            acct_name="Appreciation",
            acct_type=AcctType.EXP,
            chart=total_expense.chart,
            currency=None
        )
        impa = Account(
            acct_id=SystemAcctNumber.IMPAIRMENT,
            acct_name="Impairment",
            acct_type=AcctType.EXP,
            chart=total_expense.chart,
            currency=None
        )
        
        self.add_account(input_tax)
        self.add_account(output_tax)
        self.add_account(ar)
        self.add_account(ap)
        self.add_account(cc)
        self.add_account(api)
        self.add_account(treas)
        self.add_account(div)
        self.add_account(oci)
        self.add_account(sc)
        self.add_account(disc)
        self.add_account(fx_gain)
        self.add_account(bank_fee)
        self.add_account(ppne)
        self.add_account(acc_amort)
        self.add_account(amort)
        self.add_account(appre)
        self.add_account(impa)
        
    def create_sample(self):
        base_cur = self.setting_service.get_base_currency()
        
        total_inc_chart = self.get_chart(
            chart_id=SystemChartOfAcctNumber.TOTAL_INC
        )
        total_exp_chart = self.get_chart(
            chart_id=SystemChartOfAcctNumber.TOTAL_EXP
        )
        bank_chart = self.get_chart(
            chart_id=SystemChartOfAcctNumber.BANK_ASSET
        )
        curlib_chart = self.get_chart(
            chart_id=SystemChartOfAcctNumber.CUR_LIB
        )
        ncurlib_chart = self.get_chart(
            chart_id=SystemChartOfAcctNumber.NONCUR_LIB
        )

        consult_inc = Account(
            acct_id='acct-consul',
            acct_name='Consulting Income',
            acct_type=AcctType.INC,
            chart=total_inc_chart,
            currency=None
        )
        cogs = Account(
            acct_id='acct-cogs',
            acct_name='Cost of Service Sold',
            acct_type=AcctType.EXP,
            chart=total_exp_chart,
            currency=None
        )
        meal = Account(
            acct_id='acct-meal',
            acct_name='Meal Expense',
            acct_type=AcctType.EXP,
            chart=total_exp_chart,
            currency=None
        )
        tip = Account(
            acct_id='acct-tip',
            acct_name='Tips',
            acct_type=AcctType.EXP,
            chart=total_exp_chart,
            currency=None
        )
        rental = Account(
            acct_id='acct-rental',
            acct_name='Rental Expense',
            acct_type=AcctType.EXP,
            chart=total_exp_chart,
            currency=None
        )
        bank = Account(
            acct_id='acct-bank',
            acct_name="Bank Acct",
            acct_type=AcctType.AST,
            currency=base_cur,
            chart=bank_chart,
        )
        bank_foreign = Account(
            acct_id='acct-fbank',
            acct_name="Bank Acct (JPY)",
            acct_type=AcctType.AST,
            currency=CurType.JPY,
            chart=bank_chart
        )
        bank_foreign2 = Account(
            acct_id='acct-fbank2',
            acct_name="Bank Acct (USD)",
            acct_type=AcctType.AST,
            currency=CurType.USD,
            chart=bank_chart
        )
        credit = Account(
            acct_id='acct-credit',
            acct_name="Credit Acct",
            acct_type=AcctType.LIB,
            currency=base_cur,
            chart=curlib_chart
        )
        shareholder_loan = Account(
            acct_id='acct-shareloan',
            acct_name="Shareholder Loan",
            acct_type=AcctType.LIB,
            currency=base_cur,
            chart=ncurlib_chart
        )
        
        # add to db
        self.add_account(consult_inc)
        self.add_account(cogs)
        self.add_account(meal)
        self.add_account(tip)
        self.add_account(rental)
        self.add_account(bank)
        self.add_account(bank_foreign)
        self.add_account(bank_foreign2)
        self.add_account(credit)
        self.add_account(shareholder_loan)
        
    def clear_sample(self):
        for acct_type in AcctType:
            charts = self.get_charts(acct_type)
            for chart in charts:
                accts = self.get_accounts_by_chart(chart)
                for acct in accts:
                    self.delete_account(
                        acct_id=acct.acct_id,
                        ignore_nonexist=True,
                        restrictive=False
                    )
                    
            # clean up (delete all chart of accounts)
            self.delete_coa(acct_type)
        
    def get_coa(self, acct_type: AcctType) -> ChartNode:
        try:
            head_node = self.chart_of_acct_dao.load(acct_type=acct_type)
        except NotExistError as e:
            raise NotExistError(
                f"Root node for {acct_type} does not exist.",
                details=e.details
            )
        return head_node
        
    def save_coa(self, node: ChartNode):
        # first need to make sure the difference (charts to be deleted) does not have account attached
        # first get already existing _charts
        _charts = self.get_charts(node.chart.acct_type)
        # compare and find out charts to be deleted = _charts - charts
        charts = [n.chart for n in PreOrderIter(node)]
        chart_to_delete = [c for c in _charts if c.chart_id not in [h.chart_id for h in charts]]
        # make sure they dont have account attached
        for _chart in chart_to_delete:
            accts = self.get_accounts_by_chart(_chart)
            if len(accts) > 0:
                raise FKNoDeleteUpdateError(
                    f"Chart: {_chart} contain {len(accts)} accounts, cannot be deleted"
                )
                
        try:
            self.chart_of_acct_dao.save(node)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f'An account or chart of account belongs to the node {node}, so cannot delete it.',
                details=e.details
            )
        
    def delete_coa(self, acct_type: AcctType):
        # first need to make sure the (charts to be deleted) does not have account attached
        _charts = self.get_charts(acct_type)
        for _chart in _charts:
            accts = self.get_accounts_by_chart(_chart)
            if len(accts) > 0:
                raise FKNoDeleteUpdateError(
                    f"Chart: {_chart} contain {len(accts)} accounts, cannot be deleted"
                )
        
        self.chart_of_acct_dao.remove(acct_type)
        
    def export_coa(self, acct_type: AcctType, simple: bool = False) -> dict[str, Any]:
        root = self.get_coa(acct_type)
        return root.to_dict(simple = simple)
        
    def add_chart(self, child_chart: Chart, parent_chart_id: str):
        root = self.get_coa(child_chart.acct_type)
        parent_node = root.find_node_by_id(parent_chart_id)
        if parent_node is None:
            raise NotExistError(
                f"Parent node not found, id = {parent_chart_id}"
            )
        child_node = ChartNode(
            chart = child_chart,
            parent = parent_node
        )
        self.save_coa(root)
        
    def delete_chart(self, chart_id: str):
        chart = self.get_chart(chart_id)
        # raise error if any accounts attached to this chart
        accts = self.get_accounts_by_chart(chart)
        if len(accts) > 0:
            raise FKNoDeleteUpdateError(
                f"Cannot delete chart {chart_id} because there are {len(accts)} attached to it"
            )
        
        root = self.get_coa(chart.acct_type)
        node = root.find_node_by_id(chart_id)
        node.parent = None # remove node = dettach from the node tree
        self.save_coa(root)
        
    def update_chart(self, chart: Chart):
        root = self.get_coa(chart.acct_type)
        node = root.find_node_by_id(chart.chart_id)
        node.name = chart.name
        node.chart = chart
        node.chart_id = chart.chart_id
        self.save_coa(root)
        
    def move_chart(self, chart_id: str, new_parent_chart_id: str):
        if chart_id == new_parent_chart_id:
            raise OpNotPermittedError(
                message="Cannot move to same chart",
                details=f"chart_id = new_parent_chart_id = {chart_id}"
            )
        chart = self.get_chart(chart_id)
        root = self.get_coa(chart.acct_type)
        new_parent_node = root.find_node_by_id(new_parent_chart_id)
        current_node = root.find_node_by_id(chart_id)
        current_node.parent = new_parent_node # set a new parent
        self.save_coa(root)
        
        
    def get_chart(self, chart_id: str) -> Chart:
        try:
            chart = self.chart_of_acct_dao.get_chart(chart_id=chart_id)
        except NotExistError as e:
            raise NotExistError(
                f"Chart {chart_id} not exist.",
                details=e.details
            )
        return chart
    
    def get_parent_chart(self, chart_id: str) -> Chart | None:
        try:
            parent_chart = self.chart_of_acct_dao.get_parent_chart(chart_id=chart_id)
        except NotExistError as e:
            parent_chart = None # not exist or top node
        return parent_chart

    def get_charts(self, acct_type: AcctType) -> list[Chart]:
        try:
            charts = self.chart_of_acct_dao.get_charts(
                acct_type=acct_type
            )
        except NotExistError as e:
            raise NotExistError(
                f"Chart of Acct Type: {acct_type} not exist.",
                details=e.details
            )
        return charts
            
    def get_account(self, acct_id: str) -> Account:
        try:
            chart_id = self.acct_dao.get_chart_id_by_acct(acct_id)
        except NotExistError as e:
            raise NotExistError(
                f'Acct Id: {acct_id} not exist',
                details=e.details
            )
        
        try:
            chart = self.chart_of_acct_dao.get_chart(chart_id)
        except NotExistError as e:
            raise NotExistError(
                f'Chart Id: {chart_id} not exist',
                details=e.details
            )
        
        try:
            acct = self.acct_dao.get(acct_id, chart)
        except NotExistError as e:
            raise NotExistError(
                f'Acct Id: {acct_id} not exist',
                details=e.details
            )
        return acct
    
    def get_accounts_by_chart(self, chart: Chart) -> list[Account]:
        try:
            accts = self.acct_dao.get_accts_by_chart(chart)
        except NotExistError as e:
            accts = []
        return accts
            
    
    def add_account(self, acct: Account, ignore_exist: bool = False):
        # verify chart exists and not changed
        try:
            _chart = self.get_chart(chart_id = acct.chart.chart_id)
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
            self.acct_dao.add(acct)
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
            
    def update_account(self, acct: Account, ignore_nonexist: bool = False):
        # verify chart exists and not changed
        try:
            _chart = self.get_chart(chart_id = acct.chart.chart_id)
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
            _acct = self.get_account(acct.acct_id)
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
            self.acct_dao.update(acct)
        except FKNotExistError as e:
            raise FKNotExistError(
                f"Chart: {acct.chart} of the updated account does not exist",
                details=e.details
            )
            
    def upsert_account(self, acct: Account):
        try:
            self.add_account(acct)
        except AlreadyExistError:
            try:
                self.update_account(acct)
            except ValueError as e:
                raise e
            except FKNotExistError as e:
                raise e
        except FKNotExistError as e:
            raise e
    
    def delete_account(self, acct_id: str, ignore_nonexist: bool = False, 
                       restrictive: bool = True):
        if restrictive:
            # cannot delete system created accounts
            if acct_id in SystemAcctNumber.list_():
                raise OpNotPermittedError(
                    f"Acct id {acct_id} is system account, not permitted to delete"
                )
        
        try:
            self.acct_dao.remove(acct_id)
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