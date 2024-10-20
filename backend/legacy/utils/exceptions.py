
class DatabaseError(Exception):
    pass

class DuplicateEntryError(DatabaseError):
    pass