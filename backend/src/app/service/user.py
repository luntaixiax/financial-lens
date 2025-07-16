from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, NotExistError
from src.app.dao.user import userDao
from src.app.model.user import UserCreate, User

class UserService:
    
    def __init__(self, user_dao: userDao):
        self.user_dao = user_dao
        
    def create_user(self, user: UserCreate):
        try:
            self.user_dao.add(user)
        except AlreadyExistError as e:
            raise AlreadyExistError(
                f"User {user.username} already exist",
                details="N/A" # don't pass database info
            )
        
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