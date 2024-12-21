import logging
import pytest
from unittest import mock
from src.app.model.enums import AcctType

@pytest.fixture(scope='module')
def engine_with_basic_choa(engine):
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
def engine_with_sample_choa(engine_with_basic_choa):
    with mock.patch("src.app.dao.connection.get_engine") as mock_engine:
        mock_engine.return_value = engine_with_basic_choa
        
        from src.app.service.acct import AcctService
        
        print("Adding sample Acct and COA...")
        AcctService.create_sample()
        
        yield engine_with_basic_choa
        
        