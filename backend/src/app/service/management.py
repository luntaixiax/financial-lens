from datetime import datetime
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, NotExistError
from src.app.dao.init import initDao
from src.app.dao.user import userDao
from src.app.dao.backup import adminBackupDao
from src.app.model.user import UserCreate, User

### Operations that only admin should do ###

class InitService:
    
    def __init__(self, init_dao: initDao):
        self.init_dao = init_dao
        
    def init_common_db(self):
        self.init_dao.init_common_db()
        
class UserService:
    
    def __init__(self, user_dao: userDao, init_dao: initDao):
        self.user_dao = user_dao
        self.init_dao = init_dao
        
    def create_user(self, user: UserCreate):
        try:
            self.user_dao.add(user)
        except AlreadyExistError as e:
            raise AlreadyExistError(
                f"User {user.username} already exist",
                details="N/A" # don't pass database info
            )
        else:
            # create user specific db
            self.init_dao.init_user_db(user.user_id)
        
    def remove_user(self, user_id: str):
        try:
            self.user_dao.remove(user_id)
        except NotExistError as e:
            raise NotExistError(
                f"User {user_id} does not exist",
                details="N/A" # don't pass database info
            )
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"User {user_id} is associated with other data, cannot delete",
                details=e.details
            )
        else:
            # remove user specific db
            self.init_dao.remove_user_db(user_id)
            
    def remove_user_by_name(self, username: str):
        try:
            self.user_dao.remove_by_name(username)
        except NotExistError as e:
            raise NotExistError(
                f"User {username} does not exist",
                details="N/A" # don't pass database info
            )
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"User {username} is associated with other data, cannot delete",
                details=e.details
            )
        
        
    def update_user(self, user: UserCreate):
        try:
            self.user_dao.update(user)
        except NotExistError as e:
            raise NotExistError(
                f"User {user.username} does not exist",
                details="N/A" # don't pass database info 
            )
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"User {user} is associated with other data, cannot update",
                details=e.details
            )
        
    def get_user(self, user_id: str) -> User:
        try:
            return self.user_dao.get(user_id)
        except NotExistError as e:
            raise NotExistError(
                f"User {user_id} does not exist",
                details="N/A" # don't pass database info
            )
            
    def get_user_by_name(self, username: str) -> User:
        try:
            return self.user_dao.get_by_name(username)
        except NotExistError as e:
            raise NotExistError(
                f"User {username} does not exist",
                details="N/A" # don't pass database info
            )
        
    def list_user(self) -> list[User]:
        return self.user_dao.list_user()
    
class AdminBackupService:
    
    def __init__(self, backup_dao: adminBackupDao):
        self.backup_dao = backup_dao
    
    def list_backup_ids(self) -> list[str]:
        return self.backup_dao.list_backup_ids()
    
    def backup(self, backup_id: str | None) -> str:
        # use current timestamp if not given backup id
        backup_id = backup_id or datetime.now().strftime('%Y%m%dT%H%M%S')
        
        # backup database
        self.backup_dao.backup_database(backup_id)
        # backup files
        self.backup_dao.backup_files(backup_id)
        
        return backup_id
    
    def restore(self, backup_id: str):
        # need to restore database first, otherwise user specific database will not be created
        # restore database
        self.backup_dao.restore_database(backup_id)
        
        # restore files
        self.backup_dao.restore_files(backup_id)
        