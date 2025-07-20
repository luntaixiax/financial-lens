from pathlib import Path
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlmodel import Session, select, delete, case, func as f
from src.app.utils.tools import get_files_bucket
from src.app.model.misc import FileWrapper
from src.app.dao.orm import FileORM, infer_integrity_error
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError
from src.app.dao.connection import UserDaoAccess

class fileDao:
    
    def __init__(self, dao_access: UserDaoAccess):
        self.dao_access = dao_access
    
    def getFilePath(self, filename: str) -> str:
        return (Path(get_files_bucket()) / self.dao_access.user.user_id / 'files' / filename).as_posix() # type: ignore

    @classmethod
    def fromFile(cls, file: FileWrapper) -> FileORM:
        return FileORM(
            file_id=file.file_id,
            filename=file.filename,
            filehash=file.filehash # type: ignore
        )
        
    @classmethod
    def toFile(cls, content: str, file_orm: FileORM) -> FileWrapper:
        return FileWrapper(
            file_id=file_orm.file_id,
            filename=file_orm.filename,
            content=content
        )
        
    def register(self, filename: str) -> str:
        # if the file already exist on storage, but just want to register back to DB
        # return the file id
        fs = self.dao_access.file_fs
        filepath = self.getFilePath(filename)
        if fs.exists(filepath):
            with fs.open(filepath, 'rb') as obj:
                content = obj.read().decode(encoding='latin-1') # type: ignore
                file = FileWrapper(
                    filename=filename,
                    content=content
                )
            
            # register to DB
            file_orm = self.fromFile(file)
            
            self.dao_access.user_session.add(file_orm)
            try:
                self.dao_access.user_session.commit()
            except IntegrityError as e:
                self.dao_access.user_session.rollback()
                raise infer_integrity_error(e, during_creation=True)
                
            return file.file_id
            
        else:
            raise NotExistError(f"File ({filename}) not exist @ {filepath}")
        
        
    def add(self, file: FileWrapper):
        # save file to file system
        filepath = self.getFilePath(file.filename)
        fs = self.dao_access.file_fs
        with fs.open(filepath, 'wb') as obj:
            obj.write(file.content.encode('latin-1')) # type: ignore
        
        # save metadata to db
        file_orm = self.fromFile(file)
        
        self.dao_access.user_session.add(file_orm)
        try:
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise infer_integrity_error(e, during_creation=True)
            
    def get(self, file_id: str) -> FileWrapper:
        fs = self.dao_access.file_fs
        sql = select(FileORM).where(
            FileORM.file_id == file_id
        )
        try:
            p = self.dao_access.user_session.exec(sql).one() # get the file meta data
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        else:
            # load file from file system
            filepath = self.getFilePath(p.filename)
            if fs.exists(filepath):
                with fs.open(filepath, 'rb') as obj:
                    content = obj.read().decode(encoding='latin-1') # type: ignore
                    file = self.toFile(content, p)
            else:
                raise NotExistError(f"File ({file_id}) not exist @ {filepath}")
            
        return file
    
    def get_file_id_by_name(self, filename: str) -> str:
        sql = select(FileORM.file_id).where(
            FileORM.filename == filename
        )
        try:
            p = self.dao_access.user_session.exec(sql).one() # get the file meta data
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        else:
            return p.file_id
    
    def remove(self, file_id: str):
        fs = self.dao_access.file_fs
        
        sql = select(FileORM).where(FileORM.file_id == file_id)
        try:
            p = self.dao_access.user_session.exec(sql).one() # get the file meta
        except NoResultFound as e:
            raise NotExistError(details=str(e))
        else:
            # delete file from file system
            filepath = self.getFilePath(p.filename)
            
            if fs.exists(filepath):
                fs.rm(filepath, recursive=False)
        
        try:
            self.dao_access.user_session.delete(p)
            self.dao_access.user_session.commit()
        except IntegrityError as e:
            self.dao_access.user_session.rollback()
            raise FKNoDeleteUpdateError(details=str(e))
    