from pathlib import Path
from sqlmodel import Session, select, delete, case, func as f
from src.app.utils.tools import get_file_root
from src.app.model.misc import File
from src.app.dao.orm import FileORM, infer_integrity_error
from src.app.dao.connection import get_engine, get_fs
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, IntegrityError

class fileDao:
    
    @classmethod
    def getFilePath(cls, filename: str) -> str:
        return (Path(get_file_root()) / filename).as_posix()

    @classmethod
    def fromFile(cls, file: File) -> FileORM:
        return FileORM.model_validate(
            file.model_dump()
        )
        
    @classmethod
    def toFile(cls, file_orm: FileORM) -> File:
        return File.model_validate(
            file_orm.model_dump()
        )
        
    @classmethod
    def add(cls, content: bytes, file: File):
        # save file to file system
        filepath = cls.getFilePath()
        fs = get_fs()
        with fs.open(filepath, 'wb') as obj:
            obj.write(content) # TODO
        
        # save metadata to db
        with Session(get_engine()) as s:
            file_orm = cls.fromFile(file)
            
            s.add(file_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise infer_integrity_error(e, during_creation=True)
        