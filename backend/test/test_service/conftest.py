import logging
import pytest
from unittest import mock

@pytest.fixture(scope='module')
def engine_with_test_choa(engine):
    with mock.patch("src.app.dao.connection.get_engine") as mock_engine:
        mock_engine.return_value = engine
        
        from src.app.service.acct import AcctService
        
        AcctService.init()
        
    yield engine