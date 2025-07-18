from unittest import mock
from pydantic_core.core_schema import NoneSchema
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.app.dao.connection import engine_factory
from src.web.main import app
from src.web.dependency.dao import get_user_dao_access, get_common_dao_access
from src.web.dependency.auth import get_current_user, get_common_session, get_init_dao

@pytest.fixture(scope='session')
def client(test_dao_access, test_common_dao_access):
    """
    Create a test client with dependency overrides for testing FastAPI endpoints.
    """
    from src.app.dao.backup import initDao
    
    # Override authentication dependencies
    # def test_get_common_session():
    #     with Session(test_dao_access.common_engine) as common_session:
    #         yield common_session
            
    init_dao = initDao(common_engine=test_dao_access.common_engine)
    
    with (
        mock.patch.object(init_dao, "init_user_db", return_value=NoneSchema)
    ):
        #app.dependency_overrides[engine_factory('common')] = lambda: common_engine
        #app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_common_session] = lambda: test_dao_access.common_session
        app.dependency_overrides[get_init_dao] = lambda: init_dao
        app.dependency_overrides[get_common_dao_access] = lambda: test_common_dao_access
        app.dependency_overrides[get_user_dao_access] = lambda: test_dao_access
        
        # Create test client
        with TestClient(app) as test_client:
            yield test_client
        
        # Clean up overrides after tests
        app.dependency_overrides.clear()

@pytest.fixture(scope='session')
def token(test_user):
    from src.app.service.auth import create_access_token
    
    return create_access_token(
        user=test_user,
        secret_key='abcdefghijklmnopqrstuvwxyz',
        algorithm='HS256',
        expires_minutes=15
    )


@pytest.fixture(scope='session')
def authorized_client(client, token):
    # actually our dependency does not require login if we mock the service object
    # so using this fixture is not necessary
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {token}"
    }

    return client