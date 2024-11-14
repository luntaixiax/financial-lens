
class AlreadyExistError(FileExistsError):
    def __init__(self, message: str, details: str = "N/A"):
        super().__init__(message)
        self.details = details
        
    def __str__(self):
        return f"{self.message} (Details: {self.details})"
    
class NotExistError(FileNotFoundError):
    def __init__(self, message: str, details: str = "N/A"):
        super().__init__(message)
        self.details = details
        
    def __str__(self):
        return f"{self.message} (Details: {self.details})"

class FKNotExistError(ReferenceError):
    # creation fail because value not exist in parent table
    def __init__(self, message: str, details: str = "N/A"):
        super().__init__(message)
        self.details = details
        
    def __str__(self):
        return f"{self.message} (Details: {self.details})"
    
class FKNoDeleteUpdateError(ReferenceError):
    # delete/update fail because value exist in child table
    def __init__(self, message: str, details: str = "N/A"):
        super().__init__(message)
        self.details = details
        
    def __str__(self):
        return f"{self.message} (Details: {self.details})"
    
class OpNotPermittedError(SystemError):
    ... # does not allow to do some operation