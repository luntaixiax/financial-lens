
class AlreadyExistError(FileExistsError):
    def __init__(self, message: str = "N/A", details: str = "N/A"):
        super().__init__(message)
        self.message = message
        self.details = details
        
    def __str__(self):
        return f"{self.args[0]} (Details: {self.details})"
    
class NotExistError(FileNotFoundError):
    def __init__(self, message: str = "N/A", details: str = "N/A"):
        super().__init__(message)
        self.message = message
        self.details = details
        
    def __str__(self):
        return f"{self.args[0]} (Details: {self.details})"

class FKNotExistError(ReferenceError):
    # creation fail because value not exist in parent table
    def __init__(self, message: str = "N/A", details: str = "N/A"):
        super().__init__(message)
        self.message = message
        self.details = details
        
    def __str__(self):
        return f"{self.args[0]} (Details: {self.details})"
    
class FKNoDeleteUpdateError(ReferenceError):
    # delete/update fail because value exist in child table
    def __init__(self, message: str = "N/A", details: str = "N/A"):
        super().__init__(message)
        self.message = message
        self.details = details
        
    def __str__(self):
        return f"{self.args[0]} (Details: {self.details})"
    
class NotMatchWithSystemError(ValueError):
    # not match with system data, or not expected
    def __init__(self, message: str = "N/A", details: str = "N/A"):
        super().__init__(message)
        self.message = message
        self.details = details
        
    def __str__(self):
        return f"{self.args[0]} (Details: {self.details})"
    
class OpNotPermittedError(SystemError):
    def __init__(self, message: str = "N/A", details: str = "N/A"):
        super().__init__(message)
        self.message = message
        self.details = details
        
class PermissionDeniedError(PermissionError):
    def __init__(self, message: str = "Permission denied", details: str = "N/A"):
        super().__init__(message)
        self.message = message
        self.details = details
    