from sqlmodel import Session, select
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.dao.orm import UserORM
from src.app.model.user import User, UserCreate, UserInternalRead
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, NotExistError

class userDao:
    
    def __init__(self, session: Session):
        self.session = session
        
    def fromUser(self, user: UserCreate) -> UserORM:  
        return UserORM(
            user_id = user.user_id,
            username = user.username,
            hashed_password = user.hashed_password, # type: ignore
            is_admin = user.is_admin
        )
        
    def toUser(self, user_orm: UserORM) -> User:
        return User(
            user_id = user_orm.user_id,
            username = user_orm.username,
            is_admin = user_orm.is_admin
        )
        
    def add(self, user: UserCreate):
        user_orm = self.fromUser(user)
        self.session.add(user_orm)
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise AlreadyExistError(details=str(e))
        
    def remove(self, user_id: str):
        sql = select(UserORM).where(UserORM.user_id == user_id)
        try:
            p = self.session.exec(sql).one() # get the ccount
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        try:
            self.session.delete(p)  
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise FKNoDeleteUpdateError(details=str(e))
        
    def remove_by_name(self, username: str):
        sql = select(UserORM).where(UserORM.username == username)
        try:
            p = self.session.exec(sql).one() # get the ccount
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        try:
            self.session.delete(p)
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise FKNoDeleteUpdateError(details=str(e))
        
    def update(self, user: UserCreate):
        user_orm = self.fromUser(user)
        
        sql = select(UserORM).where(UserORM.user_id == user.user_id)
        try:
            p = self.session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        
        if not p == user_orm:
            # update
            p.username = user_orm.username
            p.hashed_password = user_orm.hashed_password # type: ignore
            p.is_admin = user_orm.is_admin
            
            self.session.add(p)
            self.session.commit()
            self.session.refresh(p) # update p to instantly have new values
            
    def get(self, user_id: str) -> User:
        sql = select(UserORM).where(UserORM.user_id == user_id)
        try:
            p = self.session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        return self.toUser(p)
            
    def get_by_name(self, username: str) -> User:
        sql = select(UserORM).where(UserORM.username == username)
        try:
            p = self.session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        return self.toUser(p)
    
    def get_internal_user_by_name(self, username: str) -> UserInternalRead:
        sql = select(UserORM).where(UserORM.username == username)
        try:
            p = self.session.exec(sql).one()
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        return UserInternalRead(
            **self.toUser(p).dict(),
            hashed_password=p.hashed_password
        )
    
    def list_user(self) -> list[User]:
        sql = select(UserORM)
        users = self.session.exec(sql).all()
        return [self.toUser(u) for u in users]