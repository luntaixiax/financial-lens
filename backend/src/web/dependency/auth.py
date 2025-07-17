from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from src.app.model.exceptions import PermissionDeniedError
from src.app.dao.connection import session_factory
from src.app.dao.user import userDao
from src.app.service.auth import AuthService
from src.app.service.user import UserService
from src.app.model.user import UserMeta

def get_user_dao(
    session: Session = Depends(session_factory('common')) # get common session
) -> userDao:
    return userDao(session=session)

def get_user_service(
    user_dao: userDao = Depends(get_user_dao)
) -> UserService:
    return UserService(user_dao=user_dao)

def get_auth_service(
    user_dao: userDao = Depends(get_user_dao)
) -> AuthService:
    return AuthService(user_dao=user_dao)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/management/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserMeta:
    return auth_service.verify_token(token)

def get_admin_user(
    user_meta: UserMeta = Depends(get_current_user),
) -> UserMeta:
    if not user_meta.is_admin:
        raise PermissionDeniedError("Admin user required")
    return user_meta