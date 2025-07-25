from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from src.app.model.user import Token, UserCreate, User, UserRegister
from src.app.service.management import AdminBackupService, UserService, InitService
from src.app.service.auth import AuthService
from src.web.dependency.service import get_init_service, get_admin_backup_service
from src.web.dependency.auth import get_auth_service, get_user_service, get_admin_user

router = APIRouter(prefix="/management", tags=["management"])

@router.post("/init_db")
def init_db(
    init_service: InitService = Depends(get_init_service),
):
    init_service.init_common_db()
    
@router.post("/create_admin_user")
def create_admin_user(
    user: UserRegister,
    user_service: UserService = Depends(get_user_service),
    admin_user: User = Depends(get_admin_user) # this for existing admin access, not the user to create
):
    user_ = UserCreate(
        username=user.username,
        is_admin=True,
        password=user.password
    )
    user_service.create_user(user_)
    
@router.post("/register")
def register(
    user: UserRegister,
    user_service: UserService = Depends(get_user_service),
):
    # everyone can register, but only open to normal user
    user_ = UserCreate(
        username=user.username,
        is_admin=False,
        password=user.password
    )
    user_service.create_user(user_)
    
@router.post("/remove_user")
def remove_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service),
    admin_user: User = Depends(get_admin_user)
):
    user_service.remove_user(user_id)
    
@router.post("/remove_user_by_name")
def remove_user_by_name(
    username: str,
    user_service: UserService = Depends(get_user_service),
    admin_user: User = Depends(get_admin_user)
):
    user_service.remove_user_by_name(username)
    
@router.post("/update_user")
def update_user(
    user: UserCreate,
    user_service: UserService = Depends(get_user_service),
    admin_user: User = Depends(get_admin_user)
):
    user_service.update_user(user)
    
@router.get("/get_user")
def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service),
    admin_user: User = Depends(get_admin_user)
) -> User:
    return user_service.get_user(user_id)

@router.get("/get_user_by_name")
def get_user_by_name(
    username: str,
    user_service: UserService = Depends(get_user_service),
    admin_user: User = Depends(get_admin_user)
) -> User:
    return user_service.get_user_by_name(username)

@router.get("/list_users")
def list_users(
    user_service: UserService = Depends(get_user_service),
    admin_user: User = Depends(get_admin_user)
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
    
@router.post("/verify_token", response_model=User)
def verify_token(
    token: str,
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    return auth_service.verify_token(token)

@router.get("/list_common_backup_ids")
def list_backup_ids(
    backup_service: AdminBackupService = Depends(get_admin_backup_service),
    admin_user: User = Depends(get_admin_user)
) -> list[str]:
    return backup_service.list_backup_ids()

@router.post("/backup_all_data")
def backup_all_data(
    backup_id: str | None = None,
    backup_service: AdminBackupService = Depends(get_admin_backup_service),
    admin_user: User = Depends(get_admin_user)
):
    return backup_service.backup(backup_id)

@router.post("/restore_all_data")
def restore_all_data(
    backup_id: str,
    backup_service: AdminBackupService = Depends(get_admin_backup_service),
    admin_user: User = Depends(get_admin_user)
):
    return backup_service.restore(backup_id)
