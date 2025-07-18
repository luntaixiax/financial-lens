from typer_di import Depends
from sqlalchemy.engine import Engine
from sqlmodel import Session
from src.app.dao.connection import CommonDaoAccess, get_engine, get_storage_fs
from src.app.dao.user import userDao
from src.app.dao.init import initDao
from src.app.dao.backup import adminBackupDao
from src.app.service.management import UserService


def get_common_engine() -> Engine:
    return get_engine('common')

def get_common_session(
    common_engine: Engine = Depends(get_common_engine)
) -> Session:
    with Session(common_engine) as common_session:
        return common_session

def get_init_dao(
    common_engine: Engine = Depends(get_common_engine)
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

def get_common_dao_access(
    common_engine: Engine = Depends(get_common_engine),
    common_session: Session = Depends(get_common_session)
) -> CommonDaoAccess:
    return CommonDaoAccess(
        common_engine=common_engine,
        common_session=common_session,
        file_fs=get_storage_fs('files'),
        backup_fs=get_storage_fs('backup')
    )
    
def get_admin_backup_dao(
    dao_access: CommonDaoAccess = Depends(get_common_dao_access)
) -> adminBackupDao:
    return adminBackupDao(dao_access=dao_access)