from typing import Any, Generator
from unittest import mock
import pytest
from src.app.model.invoice import Invoice, InvoiceItem, Item
from src.app.model.enums import AcctType, CurType, ItemType, UnitType
from src.app.model.accounts import ChartNode, Chart

@pytest.fixture
def sample_chart_of_accounts(settings) -> Generator[dict[AcctType, ChartNode], Any, Any]:
    with mock.patch("src.app.utils.tools.get_settings") as mock_settings:
        mock_settings.return_value = settings
    
        # asset chart of accounts
        total_asset = ChartNode(
            Chart(name='1000 - Total Asset', acct_type=AcctType.AST)
        )
        current_asset = ChartNode(
            Chart(name='1100 - Current Asset', acct_type=AcctType.AST), 
            parent = total_asset
        )
        noncurrent_asset = ChartNode(
            Chart(name='1200 - Non-Current Asset', acct_type=AcctType.AST), 
            parent = total_asset
        )
        bank = ChartNode(
            Chart(name='1110 - Bank', acct_type=AcctType.AST),
            parent = current_asset
        )
        
        # liability chart of accounts
        total_liability = ChartNode(
            Chart(name='2000 - Total Liability', acct_type=AcctType.LIB)
        )
        current_liability = ChartNode(
            Chart(name='2100 - Current Liability', acct_type=AcctType.LIB), 
            parent = total_liability
        )
        credit_cards = ChartNode(
            Chart(name='2110 - Credit Cards', acct_type=AcctType.LIB),
            parent = current_liability
        )
        
        # equity chart of accounts
        total_equity = ChartNode(
            Chart(name='3000 - Total Equity', acct_type=AcctType.EQU)
        )
        contributed_capital = ChartNode(
            Chart(name='3100 - Contributed Capital', acct_type=AcctType.EQU), 
            parent=total_equity
        )
        retained_earnings = ChartNode(
            Chart(name='3200 - Retained Earnings', acct_type=AcctType.EQU),
            parent=total_equity
        )
        
        # income chart of accounts
        total_income = ChartNode(
            Chart(name='4000 - Total Income', acct_type=AcctType.INC)
        )
        general_income = ChartNode(
            Chart(name='4100 - General Income', acct_type=AcctType.INC), 
            parent=total_income
        )
        investment_income = ChartNode(
            Chart(name='4200 - Investment Income', acct_type=AcctType.INC), 
            parent=total_income
        )
        
        # expense chart of accounts
        total_expense = ChartNode(
            Chart(name='5000 - Total Expense', acct_type=AcctType.EXP)
        )
        rental_utils = ChartNode(
            Chart(name='5100 - Rental & Utility', acct_type=AcctType.EXP), 
            parent=total_expense
        )
        meals_ent = ChartNode(
            Chart(name='5200 - Meals and Entertainment', acct_type=AcctType.EXP),
            parent=total_expense
        )
        
        
        yield {
            AcctType.AST: total_asset,
            AcctType.LIB: total_liability,
            AcctType.EQU: total_equity,
            AcctType.INC: total_income,
            AcctType.EXP: total_expense,
        }