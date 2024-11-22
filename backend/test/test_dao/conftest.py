
from datetime import date
from typing import Generator
from unittest import mock
import pytest
from src.app.utils.tools import get_base_cur
from src.app.model.accounts import Account, Chart, ChartNode
from src.app.model.const import SystemAcctNumber, SystemChartOfAcctNumber
from src.app.model.enums import AcctType, CurType, EntryType
from src.app.model.entity import Address, Contact, Customer
from src.app.model.journal import Entry, Journal


@pytest.fixture(scope='module')
def engine_with_test_choa(engine):
    with mock.patch("src.app.dao.connection.get_engine") as mock_engine:
        mock_engine.return_value = engine
        
        from src.app.service.acct import AcctService
        
        print("Initializing Acct and COA...")
        AcctService.init()
        
        yield engine
        
        print("Tearing down Acct and COA...")
        # clean up (delete all accounts)
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
            AcctService.delete_coa(acct_type)
            
@pytest.fixture(scope='module')
def engine_with_sample_choa(engine_with_test_choa):
    with mock.patch("src.app.dao.connection.get_engine") as mock_engine:
        mock_engine.return_value = engine_with_test_choa
        
        from src.app.service.acct import AcctService
        
        total_exp_chart = AcctService.get_chart(
            chart_id=SystemChartOfAcctNumber.TOTAL_EXP
        )
        bank_chart = AcctService.get_chart(
            chart_id=SystemChartOfAcctNumber.BANK_ASSET
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
        bank = Account(
            acct_id='acct-bank',
            acct_name="Bank Acct",
            acct_type=AcctType.AST,
            currency=get_base_cur(),
            chart=bank_chart
        )
        
        # add to db
        AcctService.add_account(meal)
        AcctService.add_account(tip)
        AcctService.add_account(bank)
        
        yield engine_with_test_choa
        
        # remove accounts
        AcctService.delete_account(meal.acct_id)
        AcctService.delete_account(tip.acct_id)
        AcctService.delete_account(bank.acct_id)
        
            
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
        chart=asset_node.find_node_by_id(SystemChartOfAcctNumber.NONCUR_ASSET).chart
    )
    ar = Account(
        acct_id=SystemAcctNumber.ACCT_RECEIV,
        acct_name="Account Receivable",
        acct_type=AcctType.AST,
        currency=get_base_cur(),
        chart=asset_node.find_node_by_id(SystemChartOfAcctNumber.CUR_ASSET).chart
    )
    check = Account(
        acct_name="TEST BANK CHECK",
        acct_type=AcctType.AST,
        currency=CurType.USD,
        chart=asset_node.find_node_by_id(SystemChartOfAcctNumber.BANK_ASSET).chart
    )
    return [input_tax, ar, check]


@pytest.fixture
def sample_journal_meal(engine_with_sample_choa) -> Generator[Journal, None, None]:
    with mock.patch("src.app.dao.connection.get_engine") as mock_engine:
        mock_engine.return_value = engine_with_test_choa
        
        from src.app.service.acct import AcctService
        
        journal = Journal(
            jrn_date=date(2024, 1, 1),
            entries=[
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=AcctService.get_account('acct-meal'),
                    cur_incexp=get_base_cur(),
                    amount=105.83,
                    amount_base=105.83,
                    description='Have KFC with client'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=AcctService.get_account('acct-tip'),
                    cur_incexp=get_base_cur(),
                    amount=13.93,
                    amount_base=13.93,
                    description='Tip for KFC'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=AcctService.get_account(SystemAcctNumber.INPUT_TAX),
                    amount=13.35,
                    amount_base=13.35,
                    description=None
                ),
                Entry(
                    entry_type=EntryType.CREDIT,
                    acct=AcctService.get_account('acct-bank'),
                    amount=133.11,
                    amount_base=133.11,
                    description=None
                ),
            ],
            is_manual=True,
            note='sample meal journal'
        )
        
        yield journal