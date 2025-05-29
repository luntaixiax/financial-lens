from pathlib import Path
from typing import Tuple
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlmodel import Session, select, delete, case, func as f
from src.app.utils.tools import get_file_root
from src.app.model.misc import FileWrapper
from src.app.dao.orm import FileORM, infer_integrity_error
from src.app.dao.connection import get_engine, get_storage_fs
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError

class fileDao:
    
    @classmethod
    def getFilePath(cls, filename: str) -> str:
        return (Path(get_file_root()) / filename).as_posix()

    @classmethod
    def fromFile(cls, file: FileWrapper) -> FileORM:
        return FileORM(
            file_id=file.file_id,
            filename=file.filename,
            filehash=file.filehash
        )
        
    @classmethod
    def toFile(cls, content: bytes, file_orm: FileORM) -> FileWrapper:
        return FileWrapper(
            file_id=file_orm.file_id,
            filename=file_orm.filename,
            content=content
        )
        
    @classmethod
    def add(cls, file: FileWrapper):
        # save file to file system
        filepath = cls.getFilePath(file.filename)
        fs = get_storage_fs()
        with fs.open(filepath, 'wb') as obj:
            obj.write(file.content.encode('latin-1')) # TODO
        
        # save metadata to db
        with Session(get_engine()) as s:
            file_orm = cls.fromFile(file)
            
            s.add(file_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise infer_integrity_error(e, during_creation=True)
            
    @classmethod
    def get(cls, file_id: str) -> FileWrapper:
        fs = get_storage_fs()
        with Session(get_engine()) as s:
            sql = select(FileORM).where(
                FileORM.file_id == file_id
            )
            try:
                p = s.exec(sql).one() # get the file meta data
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            else:
                # load file from file system
                filepath = cls.getFilePath(p.filename)
                if fs.exists(filepath):
                    with fs.open(filepath, 'rb') as obj:
                        content = obj.read().decode(encoding='latin-1')
                        file = cls.toFile(content, p)
                else:
                    raise NotExistError(f"File ({file_id}) not exist @ {filepath}")
            
        return file
    
    @classmethod
    def get_file_id_by_name(cls, filename: str) -> str:
        with Session(get_engine()) as s:
            sql = select(FileORM.file_id).where(
                FileORM.filename == filename
            )
            try:
                p = s.exec(sql).one() # get the file meta data
            except NoResultFound as e:
                raise NotExistError(details=str(e))
        
        return p
    
    @classmethod
    def remove(cls, file_id: str):
        fs = get_storage_fs()
        with Session(get_engine()) as s:
            sql = select(FileORM).where(FileORM.file_id == file_id)
            try:
                p = s.exec(sql).one() # get the file meta
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            else:
                # delete file from file system
                filepath = cls.getFilePath(p.filename)
                
                if fs.exists(filepath):
                    fs.rm(filepath, recursive=False)
            
            try:
                s.delete(p)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNoDeleteUpdateError(details=str(e))
    