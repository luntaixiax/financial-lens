from typing import Annotated, Generator
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.engine import Engine
from sqlmodel import Session
from src.app.model.user import User
from src.app.model.exceptions import PermissionDeniedError
from src.app.dao.connection import session_factory, engine_factory
from src.app.dao.user import userDao
from src.app.dao.init import initDao
from src.app.service.auth import AuthService
from src.app.service.management import UserService


common_engine_dep = Annotated[Engine, Depends(engine_factory('common'))]

def get_common_session(
    common_engine: common_engine_dep
) -> Generator[Session, None, None]:
    with Session(common_engine) as common_session:
        yield common_session

def get_init_dao(
    common_engine: common_engine_dep
) -> initDao:
    return initDao(common_engine=common_engine)

def get_user_dao(
    common_session: Session = Depends(get_common_session)
) -> userDao:
    return userDao(session=common_session)

def get_user_service(
    user_dao: userDao = Depends(get_user_dao),
    init_dao: initDao = Depends(get_init_dao)
) -> UserService:
    return UserService(user_dao=user_dao, init_dao=init_dao)

def get_auth_service(
    user_dao: userDao = Depends(get_user_dao)
) -> AuthService:
    return AuthService(user_dao=user_dao)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/management/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    return auth_service.verify_token(token)

def get_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_admin:
        raise PermissionDeniedError("Admin user required")
    return user