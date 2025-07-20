

from typer_di import Depends
from src.app.dao.backup import adminBackupDao
from src.app.dao.user import userDao
from src.app.service.management import AdminBackupService, InitService, UserService
from src.app.dao.init import initDao
from src.cli.dependency.unauth_dao import get_admin_backup_dao, get_init_dao, get_user_dao

def get_init_service(
    init_dao: initDao = Depends(get_init_dao)
) -> InitService:
    return InitService(init_dao=init_dao)

def get_user_service(
    user_dao: userDao = Depends(get_user_dao),
    init_dao: initDao = Depends(get_init_dao)
) -> UserService:
    return UserService(user_dao=user_dao, init_dao=init_dao)

def get_admin_backup_service(
    backup_dao: adminBackupDao = Depends(get_admin_backup_dao)
) -> AdminBackupService:
    return AdminBackupService(backup_dao=backup_dao)