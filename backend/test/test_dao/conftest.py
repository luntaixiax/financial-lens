
from datetime import date
from typing import Generator
from unittest import mock
import pytest
from src.app.utils.tools import get_base_cur
from src.app.model.accounts import Account, Chart, ChartNode
from src.app.model.const import SystemAcctNumber, SystemChartOfAcctNumber
from src.app.model.enums import AcctType, CurType, EntityType, EntryType, ItemType, JournalSrc, UnitType
from src.app.model.entity import Address, Contact, Customer
from src.app.model.journal import Entry, Journal
from src.app.model.invoice import Invoice, InvoiceItem, Item


@pytest.fixture(scope='module')
def engine_with_basic_choa(engine, settings):
    with mock.patch("src.app.dao.connection.get_engine")  as mock_engine, \
        mock.patch("src.app.utils.tools.get_settings") as mock_settings:
        mock_engine.return_value = engine
        mock_settings.return_value = settings
        
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
def engine_with_sample_choa(engine_with_basic_choa, settings):
   with mock.patch("src.app.dao.connection.get_engine")  as mock_engine, \
        mock.patch("src.app.utils.tools.get_settings") as mock_settings:
        mock_engine.return_value = engine_with_basic_choa
        mock_settings.return_value = settings
        
        from src.app.service.acct import AcctService
        
        print("Adding sample Acct and COA...")
        AcctService.create_sample()
        
        yield engine_with_basic_choa
        
            
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
def sample_journal_meal(engine_with_sample_choa, settings) -> Generator[Journal, None, None]:
        
    with mock.patch("src.app.dao.connection.get_engine")  as mock_engine, \
        mock.patch("src.app.utils.tools.get_settings") as mock_settings:
        mock_engine.return_value = engine_with_sample_choa
        mock_settings.return_value = settings
        
        
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
            jrn_src=JournalSrc.MANUAL,
            note='sample meal journal'
        )
        
        yield journal
        
@pytest.fixture
def sample_items() -> list[Item]:
    item_consult = Item(
        name='Item - Consulting',
        item_type=ItemType.SERVICE,
        entity_type=EntityType.CUSTOMER,
        unit=UnitType.HOUR,
        unit_price=100,
        currency=CurType.USD,
        default_acct_id='acct-consul'
    )
    item_meeting = Item(
        name='Item - Meeting',
        item_type=ItemType.SERVICE,
        entity_type=EntityType.CUSTOMER,
        unit=UnitType.HOUR,
        unit_price=75,
        currency=CurType.USD,
        default_acct_id='acct-consul'
    )
    return [item_consult, item_meeting]

@pytest.fixture
def sample_invoice(engine_with_sample_choa, sample_items, customer1) -> Generator[Invoice, None, None]:
    with mock.patch("src.app.dao.connection.get_engine") as mock_engine:
        mock_engine.return_value = engine_with_sample_choa
        
        from src.app.dao.invoice import itemDao
        from src.app.dao.entity import customerDao, contactDao
        
        # add customer
        contactDao.add(contact = customer1.bill_contact)
        customerDao.add(customer1)
        
        # add items
        for item in sample_items:
            itemDao.add(item)
        
        # create invoice
        invoice = Invoice(
            invoice_id='inv-sample',
            invoice_num='INV-001',
            invoice_dt=date(2024, 1, 1),
            due_dt=date(2024, 1, 5),
            entity_id=customer1.cust_id,
            entity_type=EntityType.CUSTOMER,
            subject='General Consulting - Jan 2024',
            currency=CurType.USD,
            invoice_items=[
                InvoiceItem(
                    item=sample_items[0],
                    quantity=5,
                    description="Programming"
                ),
                InvoiceItem(
                    item=sample_items[1],
                    quantity=10,
                    description="Meeting Around",
                    discount_rate=0.05,
                )
            ],
            shipping=10,
            note="Thanks for business"
        )
        
        
        yield invoice
        
        # delete items
        for item in sample_items:
            itemDao.remove(item.item_id)
        customerDao.remove(customer1.cust_id)
        contactDao.remove(customer1.bill_contact.contact_id)