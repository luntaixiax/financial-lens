
import pytest
from src.app.utils.tools import get_base_cur
from src.app.model.accounts import Account, Chart, ChartNode
from src.app.model.const import SystemAcctNumber, SystemChartOfAcctNumber
from src.app.model.enums import AcctType, CurType
from src.app.model.entity import Address, Contact, Customer


@pytest.fixture
def contact1() -> Contact:
    return Contact(
        name='luntaixia',
        email='infodesk@ltxservice.ca',
        phone='123456789',
        address=Address(
            address1='00 XX St E',
            suite_no=1234,
            city='Toronto',
            state='ON',
            country='Canada',
            postal_code='XYZABC'
        )
    )
    
@pytest.fixture
def customer1(contact1) -> Customer:
    return Customer(
        customer_name = 'LTX Company',
        is_business=True,
        bill_contact=contact1,
        ship_same_as_bill=True
    )
    

@pytest.fixture
def asset_node() -> ChartNode:
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
    return total_asset

@pytest.fixture
def sample_accounts(asset_node: ChartNode) -> list[Account]:
    
    # create system accounts (tax, AR/AP, etc.)
    input_tax = Account(
        acct_id=SystemAcctNumber.INPUT_TAX,
        acct_name="Input Tax",
        acct_type=AcctType.AST,
        currency=get_base_cur(),
        chart=asset_node.find_node_by_id(SystemChartOfAcctNumber.NONCUR_ASSET)
    )
    ar = Account(
        acct_id=SystemAcctNumber.ACCT_RECEIV,
        acct_name="Account Receivable",
        acct_type=AcctType.AST,
        currency=get_base_cur(),
        chart=asset_node.find_node_by_id(SystemChartOfAcctNumber.CUR_ASSET)
    )
    check = Account(
        acct_name="TEST BANK CHECK",
        acct_type=AcctType.AST,
        currency=CurType.USD,
        chart=asset_node.find_node_by_id(SystemChartOfAcctNumber.BANK_ASSET)
    )
    return [input_tax, ar, check]