from enum import IntEnum, unique

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
class AcctType(IntEnum):
    AST = 1
    LIB = 2
    EQU = 3
    INC = 4
    EXP = 5
    
@unique
class EntryType(IntEnum):
    DEBIT = 1
    CREDIT = 2

    
@unique
class BankAcctType(IntEnum):
    CHQ = 1
    SAV = 2
    CREDIT = 3
    LOAN = 4
    
@unique
class ItemType(IntEnum):
    SERVICE = 1
    GOOD = 2
    
@unique
class UnitType(IntEnum):
    HOUR = 1
    DAY = 2
    WEEK = 3
    MONTH = 4
    PIECE = 5
    KG = 6
    
@unique
class JournalSrc(IntEnum):
    MANUAL = 1
    INVOICE = 2
    PURCHASE = 3
    PAYMENT = 4
    EXPENSE = 5
    
@unique
class PaymentDirection(IntEnum):
    PAY = 1
    RECEIVE = 2
    
@unique
class EntityType(IntEnum):
    CUSTOMER = 1
    SUPPLIER = 2