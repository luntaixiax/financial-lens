from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError
from src.app.model.misc import FileWrapper
from src.app.dao.files import fileDao

class FileService:
    
    @classmethod
    def add_file(cls, file: FileWrapper):
        try:
            fileDao.add(file)
        except AlreadyExistError as e:
            raise AlreadyExistError(
                message='File already exist',
                details=e.details
            )
        except FKNotExistError as e:
            raise FKNotExistError(
                message='Some component of file does not exist',
                details=e.details
            )
            
    @classmethod
    def delete_file(cls, file_id: str):
        try:
            fileDao.remove(file_id)
        except NotExistError as e:
            raise NotExistError(
                message=f"File not exist: {file_id}",
                details=e.details
            )
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                message='Some component of file prevent file being deleted',
                details=e.details
            )
            
    @classmethod
    def get_file(cls, file_id: str) -> FileWrapper:
        try:
            file = fileDao.get(file_id)
        except NotExistError as e:
            raise NotExistError(
                message=f"File not exist: {file_id}",
                details=e.details
            )
        return file
    