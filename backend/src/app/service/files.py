from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError, NotMatchWithSystemError, OpNotPermittedError
from src.app.model.misc import FileWrapper
from src.app.dao.files import fileDao

class FileService:
    
    def __init__(self, file_dao: fileDao):
        self.file_dao = file_dao
        
    def register_file(self, filename: str) -> str:
        # if the file already exist on storage, but just want to register back to DB
        try:
            file_id = self.file_dao.register(filename)
        except NotExistError as e:
            raise NotExistError(
                message=f"File not exist",
                details=f"{filename}"
            )
        except AlreadyExistError as e:
            raise AlreadyExistError(
                message=f"File already exist",
                details=f"{filename}"
            )
        
        return file_id
        
    def register_files(self, filenames: list[str]) -> dict[str, str]:
        # return {filename: file_id}
        errs = []
        err_files = []
        dup_files = []
        maps = {}
        for i, filename in enumerate(filenames):
            try:
                file_id = self.register_file(filename)
            except (NotExistError, FKNotExistError, NotMatchWithSystemError, FKNoDeleteUpdateError, OpNotPermittedError) as e:
                errs.append(e)
                err_files.append(filename)
            except AlreadyExistError as e:
                dup_files.append(filename)
                maps[filename] = self.file_dao.get_file_id_by_name(filename) # must record as well
                
            else:
                
                # not to pressure db # TODO optimize
                # if i % 10:
                #     sleep(1)
                maps[filename] = file_id
        
        if len(err_files) > 0:
            raise OpNotPermittedError(
                message="Several files not registered due to error",
                details="\n".join(f"Error ({er}), Expense {exp}" for er, exp in zip(errs, err_files))
            )
        
        return maps
    
    def add_file(self, file: FileWrapper):
        try:
            self.file_dao.add(file)
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
            
    def delete_file(self, file_id: str):
        try:
            self.file_dao.remove(file_id)
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
            
    def get_file(self, file_id: str) -> FileWrapper:
        try:
            file = self.file_dao.get(file_id)
        except NotExistError as e:
            raise NotExistError(
                message=f"File not exist: {file_id}",
                details=e.details
            )
        return file
    
    def get_file_id_by_name(self, filename: str) -> str:
        try:
            return self.file_dao.get_file_id_by_name(filename)
        except NotExistError as e:
            raise NotExistError(
                message=f"File not exist: {filename}",
                details=e.details
            )