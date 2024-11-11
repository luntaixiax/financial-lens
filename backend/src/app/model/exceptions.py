
class AlreadyExistError(FileExistsError):
    ...
    
class NotExistError(FileNotFoundError):
    ...

class FKNotExistError(ReferenceError):
    # creation fail because value not exist in parent table
    ...
    
class FKNoDeleteUpdateError(ReferenceError):
    # delete/update fail because value exist in child table
    ...