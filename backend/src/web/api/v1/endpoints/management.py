from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from src.app.model.user import Token, UserCreate, User, UserMeta
from src.app.service.user import UserService
from src.app.service.backup import BackupService
from src.app.service.auth import AuthService
from src.web.dependency.service import get_auth_service, get_backup_service, get_user_service

router = APIRouter(prefix="/management", tags=["management"])

@router.post("/init_db")
def init_db(
    backup_service: BackupService = Depends(get_backup_service)
):
    backup_service.init_db()
    
@router.post("/create_user")
def create_user(
    user: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    user_service.create_user(user)
    
@router.post("/remove_user")
def remove_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    user_service.remove_user(user_id)
    
@router.post("/remove_user_by_name")
def remove_user_by_name(
    username: str,
    user_service: UserService = Depends(get_user_service)
):
    user_service.remove_user_by_name(username)
    
@router.post("/update_user")
def update_user(
    user: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    user_service.update_user(user)
    
@router.get("/get_user")
def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
) -> User:
    return user_service.get_user(user_id)

@router.get("/get_user_by_name")
def get_user_by_name(
    username: str,
    user_service: UserService = Depends(get_user_service)
) -> User:
    return user_service.get_user_by_name(username)

@router.get("/list_users")
def list_users(
    user_service: UserService = Depends(get_user_service)
) -> list[User]:
    return user_service.list_user()


@router.post("/login", response_model=Token)
def login(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    return auth_service.login(
        username=user_credentials.username, 
        password=user_credentials.password
    )

@router.get("/list_backup_ids")
def list_backup_ids(
    backup_service: BackupService = Depends(get_backup_service)
) -> list[str]:
    return backup_service.list_backup_ids()

@router.post("/backup")
def backup(
    backup_id: str | None = None,
    backup_service: BackupService = Depends(get_backup_service)
) -> str:
    return backup_service.backup(backup_id)

@router.post("/restore")
def restore(
    backup_id: str,
    backup_service: BackupService = Depends(get_backup_service)
):
    backup_service.restore(backup_id)
