from enum import Enum, IntEnum, unique, auto

@unique
class CurType(IntEnum):
    USD = 1
    CAD = 2
    CNY = 3
    GBP = 4
    AUD = 5
    JPY = 6
    EUR = 7
    MOP = 8
    HKD = 9
    CHF = 10
    TWD = 11
    THB = 12
    MXN = 13
    CUP = 14
    RUB = 15
    
    
@unique
class RoleType(IntEnum):
    STAFF = 1 # normal employee
    MANAGER = 2 # executives
    DIRECTOR = 3 # board members
    
@unique
class BalShType(IntEnum):
    AST = 1
    LIB = 2
    EQU = 3
    
@unique
class IncExpType(IntEnum):
    INC = 1
    EXP = 2
    
@unique
class EntryType(IntEnum):
    DEBIT = 1
    CREDIT = 2
    
@unique
class EntityType(IntEnum):
    PERS = 1
    CORP = 2
    
@unique
class EventType(IntEnum):
    ESSENTIAL = 1 # daily, fixed income/expense
    OPTIONAL = 2 # optional, quality improve
    OCCASSION = 3 # occasionally, jianzhi, travel, tourism
    INV = 4 # investmet related, financing, gain/loss
    AMORT = 5 # amortization and depreciation
    TRANSFER = 6 # transfer related
    OTHER = 7 # any other types