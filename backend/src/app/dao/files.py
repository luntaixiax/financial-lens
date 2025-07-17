from functools import lru_cache
from pathlib import Path
from typing import Any, Tuple
import json
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlmodel import Session, select, delete, case, func as f
from src.app.utils.tools import get_file_root, get_config_root
from src.app.model.misc import FileWrapper
from src.app.dao.orm import FileORM, infer_integrity_error
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError
from s3fs import S3FileSystem
from src.app.dao.connection import UserDaoAccess

class configDao:
    # json config file, can be replaced by nosql db
    CONFIG_FILENAME = 'config.json'
    
    def __init__(self, dao_access: UserDaoAccess):
        self.dao_access = dao_access
    
    @classmethod
    def getConfigPath(cls) -> str:
        return (Path(get_config_root()) / cls.CONFIG_FILENAME).as_posix()
    
    @lru_cache
    def get_config(self) -> dict[str, Any]:
        filepath = self.getConfigPath()
        fs = self.dao_access.file_fs
        try:
            with fs.open(filepath, 'r') as obj:
                config = json.load(obj)
        except FileNotFoundError as e:
            return {}
        
        # TODO: add error handling when config is not exist
        return config
    
    def get_config_value(self, key: str) -> Any:
        return self.get_config().get(key)
    
    def set_config_value(self, key: str, value: Any):
        config = self.get_config()
        config[key] = value
        
        # write config back
        filepath = self.getConfigPath()
        fs = self.dao_access.file_fs
        with fs.open(filepath, 'w') as obj:
            json.dump(config, obj, indent=4)
        
        # clear cache
        self.get_config.cache_clear()
    
    

class fileDao:
    
    def __init__(self, dao_access: UserDaoAccess):
        self.dao_access = dao_access
    
    @classmethod
    def getFilePath(cls, filename: str) -> str:
        return (Path(get_file_root()) / filename).as_posix() # type: ignore

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
    