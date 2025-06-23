from typing import List, Dict, Tuple
from sqlmodel import Field, SQLModel, Column, create_engine
from sqlalchemy import ForeignKey, Boolean, JSON, ARRAY, Integer, String, Text, Date, DECIMAL, inspect, INT, CHAR
from sqlalchemy_utils import EmailType, PasswordType, PhoneNumberType, ChoiceType
from sqlalchemy.exc import NoResultFound, IntegrityError
from datetime import date

from src.app.model.exceptions import FKNoDeleteUpdateError, FKNotExistError, AlreadyExistError
from src.app.model.enums import AcctType, BankAcctType, CurType, EntityType, EntryType, ItemType, JournalSrc, PropertyTransactionType, PropertyType, UnitType

def infer_integrity_error(e: IntegrityError, during_creation: bool = True) ->  FKNoDeleteUpdateError | FKNotExistError | AlreadyExistError | IntegrityError:
    # TODO: enhance this when use other backend engine
    origin_message = str(e.orig).lower()
    if 'foreign key' in origin_message:
        # sqlite message: FOREIGN KEY constraint failed
        # mysql message: a foreign key constraint fails
        if during_creation:
            # during object creation, error = entry does not exist in child/lower level table
            # e.g., if contact does not exist, customer should not be created
            return FKNotExistError(details=str(e))
        else:
            # during update/delete, error = on_delete/on_update failed
            return FKNoDeleteUpdateError(details=str(e))
    if 'unique' in origin_message or 'duplicate' in origin_message:
        # sqlite message: UNIQUE constraint failed
        # mysql message: Duplicate entry
        return AlreadyExistError(details=str(e))
    
    return e

def get_class_by_tablename(tablename):
    """Return class reference mapped to table.

    :param tablename: String with name of table.
    :return: Class reference or None.
    """
    for c in SQLModelWithSort._sa_registry.mappers:
        if hasattr(c, 'class_') and c.class_.__tablename__ == tablename:
            return c.class_

class SQLModelWithSort(SQLModel):
    
    @classmethod
    def sort_for_backup(cls, rows):
        # sort rows from query, useful in case of backup
        return rows
    
class FileORM(SQLModelWithSort, table=True):
    __tablename__ = 'file'
    
    file_id: str = Field(
        sa_column=Column(
            String(length = 18), 
            primary_key = True, 
            nullable = False)
    )
    filename: str = Field(sa_column=Column(String(length = 200), nullable = False, primary_key = False, unique=True))
    filehash: str = Field(sa_column=Column(String(length = 64), nullable = False, primary_key = False, unique=True))

class FxORM(SQLModelWithSort, table=True):
    __tablename__ = "currency"
    
    currency: CurType = Field(
        sa_column=Column(
            ChoiceType(CurType, impl = Integer()), 
            primary_key = True, 
            nullable = False
        )
    )
    cur_dt: date = Field(
        sa_column=Column(Date(), primary_key = True, nullable = False)
    )
    rate: float = Field(
        sa_column=Column(DECIMAL(15, 5, asdecimal=False), nullable = False)
    )
    
    
class ContactORM(SQLModelWithSort, table=True):
    
    __tablename__ = "contact"
    
    contact_id: str = Field(
        sa_column=Column(
            String(length = 13), 
            primary_key = True, 
            nullable = False)
    )
    name: str = Field(sa_column=Column(String(length = 50), nullable = False, unique = True))
    email: str = Field(sa_column=Column(EmailType(), nullable = False))
    phone: str = Field(sa_column=Column(PhoneNumberType(), nullable = True))
    address: dict | None = Field(sa_column=Column(JSON(), nullable = True))


class EntityORM(SQLModelWithSort, table=True):
    __tablename__ = "entity"
    
    entity_id: str = Field(
        sa_column=Column(
            String(length = 13), 
            primary_key = False, 
            nullable = False,
            unique=True
        )
    )
    entity_type: EntityType = Field(
        sa_column=Column(ChoiceType(EntityType, impl = Integer()), nullable = False, primary_key = True)
    )
    entity_name: str = Field(sa_column=Column(String(length = 50), nullable = False, primary_key = True))
    is_business: EntryType = Field(
        sa_column=Column(
            Boolean(create_constraint=True), 
            default = True, 
            nullable = False
        )
    )
    bill_contact_id: str = Field(
        sa_column=Column(
            String(length = 13),
            ForeignKey(
                'contact.contact_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            nullable = False
        )
    )
    ship_same_as_bill: bool = Field(
        sa_column=Column(
            Boolean(create_constraint=True), 
            default = True, 
            nullable = False
        )
    )
    ship_contact_id: str | None = Field(
        sa_column=Column(
            String(length = 13),
            ForeignKey(
                'contact.contact_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            nullable = False
        )
    )
    

class ChartOfAccountORM(SQLModelWithSort, table=True):
    
    __tablename__ = "chart_of_account"
    
    chart_id: str = Field(
        sa_column=Column(
            String(length = 13), 
            primary_key = True, 
            nullable = False
        )
    )
    node_name: str = Field(
        sa_column=Column(String(length = 50), primary_key = False, nullable = False, unique = True)
    )
    acct_type: AcctType = Field(
        sa_column=Column(ChoiceType(AcctType, impl = Integer()), nullable = False)
    )
    parent_chart_id: str | None = Field(
        sa_column=Column(
            String(length = 13),
            ForeignKey(
                'chart_of_account.chart_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            nullable = True
        )
    )
    
    @classmethod
    def sort_for_backup(cls, rows):
        
        from anytree import Node, RenderTree, PreOrderIter
        
        # need this top node for all charts from different branch
        nodes = {
            'top_node': Node('top_node')
        }
        
        # add all nodes and save mappings
        mappings = {}
        for r in rows:
            chart_id = r.chart_id
            parent_chart_id = r.parent_chart_id or 'top_node'
            
            nodes[chart_id] = Node(name=chart_id)
            mappings[chart_id] = {
                'chart_id': chart_id,
                'parent_chart_id': parent_chart_id,
                'row': r
            }
        
        # 2nd iteration: add dependency
        for chart_id, m in mappings.items():
            parent_chart_id = m.get('parent_chart_id')
            nodes[chart_id].parent = nodes[parent_chart_id]
        
        ordered = []
        for node in PreOrderIter(nodes['top_node']):
            if node.name == 'top_node':
                continue
            
            ordered.append(mappings[node.name]['row'])
            
        return ordered
    
    
class AcctORM(SQLModelWithSort, table=True):
    
    __tablename__ = "accounts"
    
    acct_id: str = Field(
        sa_column=Column(String(length = 15), primary_key = True, nullable = False)
    )
    acct_name: str = Field(
        sa_column=Column(String(length = 50), nullable = False, unique = True)
    )
    acct_type: AcctType = Field(
        sa_column=Column(ChoiceType(AcctType, impl = Integer()), nullable = False)
    )
    currency: CurType | None = Field(
        sa_column=Column(ChoiceType(CurType, impl = Integer()), nullable = True)
    )
    chart_id: str = Field(
        sa_column=Column(
            String(length = 13),
            ForeignKey(
                'chart_of_account.chart_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            nullable = False
        )
    )
    
class JournalORM(SQLModelWithSort, table=True):
    
    __tablename__ = "journals"
    
    journal_id: str = Field(
        sa_column=Column(String(length = 20), primary_key = True, nullable = False)
    )
    jrn_date: date = Field(sa_column=Column(Date(), nullable = False))
    jrn_src: JournalSrc | None = Field(
        sa_column=Column(ChoiceType(JournalSrc, impl = Integer()), nullable = False)
    )
    note: str | None = Field(sa_column=Column(Text(), nullable = True))
    
class EntryORM(SQLModelWithSort, table=True):
    __tablename__ = "entries"
    
    entry_id: str = Field(
        sa_column=Column(String(length = 20), primary_key = True, nullable = False)
    )
    journal_id: str = Field(
        sa_column=Column(
            String(length = 20),
            ForeignKey(
                'journals.journal_id', 
                onupdate = 'CASCADE', 
                ondelete = 'CASCADE'
            ),
            primary_key = False, 
            nullable = False
        )
    )
    entry_type: EntryType = Field(
        sa_column=Column(ChoiceType(EntryType, impl = Integer()), nullable = False)
    )
    acct_id: str = Field(
        sa_column=Column(
            String(length = 15), 
            ForeignKey(
                'accounts.acct_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            primary_key = False, 
            nullable = False
        )
    )
    cur_incexp: CurType | None = Field(
        sa_column=Column(ChoiceType(CurType, impl = Integer()), nullable = True)
    )
    amount: float = Field(sa_column=Column(DECIMAL(18, 6 , asdecimal=False), nullable = False, server_default = "0.0"))
    amount_base: float = Field(sa_column=Column(DECIMAL(18, 6 , asdecimal=False), nullable = False, server_default = "0.0"))
    description: str | None = Field(sa_column=Column(Text(), nullable = True))
    
    
class ItemORM(SQLModelWithSort, table=True):
    __tablename__ = "item"
    
    item_id: str = Field(
        sa_column=Column(String(length = 13), primary_key = True, nullable = False)
    )
    name: str = Field(
        sa_column=Column(String(length = 50), primary_key = False, nullable = False)
    )
    item_type: ItemType = Field(
        sa_column=Column(ChoiceType(ItemType, impl = Integer()), nullable = False)
    )
    entity_type: EntityType = Field(
        sa_column=Column(ChoiceType(EntityType, impl = Integer()), nullable = False, primary_key = False)
    )
    unit: UnitType = Field(
        sa_column=Column(ChoiceType(UnitType, impl = Integer()), nullable = False)
    )
    unit_price: float = Field(sa_column=Column(DECIMAL(15, 3 , asdecimal=False), nullable = False, server_default = "0.0"))
    currency: CurType | None = Field(
        sa_column=Column(ChoiceType(CurType, impl = Integer()), nullable = True)
    )
    default_acct_id: str = Field(
        sa_column=Column(
            String(length = 15), 
            ForeignKey(
                'accounts.acct_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            primary_key = False, 
            nullable = False
        )
    )


class InvoiceORM(SQLModelWithSort, table=True):
    __tablename__ = "invoice"
    
    invoice_id: str = Field(
        sa_column=Column(String(length = 13), primary_key = True, nullable = False)
    )
    invoice_num: str = Field(
        sa_column=Column(String(length = 25), primary_key = False, nullable = False, unique = True)
    )
    invoice_dt: date = Field(sa_column=Column(Date(), nullable = False))
    due_dt: date | None = Field(sa_column=Column(Date(), nullable = True))
    entity_id: str = Field(
        sa_column=Column(
            String(length = 13),
            ForeignKey(
                'entity.entity_id',
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            primary_key = False, 
            nullable = False
        )
    )
    entity_type: EntityType = Field(
        sa_column=Column(ChoiceType(EntityType, impl = Integer()), nullable = False, primary_key = False)
    )
    subject: str = Field(
        sa_column=Column(String(length = 50), primary_key = False, nullable = False)
    )
    currency: CurType | None = Field(
        sa_column=Column(ChoiceType(CurType, impl = Integer()), nullable = True)
    )
    shipping: float = Field(sa_column=Column(DECIMAL(15, 3 , asdecimal=False), nullable = False, server_default = "0.0"))
    journal_id: str = Field(
        sa_column=Column(
            String(length = 20),
            ForeignKey(
                'journals.journal_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT' # TODO: review this
            ),
            primary_key = False, 
            nullable = False
        )
    ) # TODO: in dao, need to add journal (auto mode) first, then add invoice
    note: str | None = Field(sa_column=Column(Text(), nullable = True))
    

class InvoiceItemORM(SQLModelWithSort, table=True):
    __tablename__ = "invoice_item"
    
    invoice_item_id: str = Field(
        sa_column=Column(String(length = 17), primary_key = True, nullable = False)
    )
    invoice_id: str = Field(
        sa_column=Column(
            String(length = 13), 
            ForeignKey(
                'invoice.invoice_id', 
                onupdate = 'CASCADE', 
                ondelete = 'CASCADE' # TODO
            ),
            primary_key = False, 
            nullable = False
        )
    )
    item_id: str = Field(
        sa_column=Column(
            String(length = 13), 
            ForeignKey(
                'item.item_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            primary_key = False, 
            nullable = False
        )
    )
    quantity: float = Field(sa_column=Column(DECIMAL(18, 8 , asdecimal=False), nullable = False, server_default = "0.0"))
    acct_id: str = Field(
        sa_column=Column(
            String(length = 15), 
            ForeignKey(
                'accounts.acct_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            primary_key = False, 
            nullable = False
        )
    )
    tax_rate: float = Field(sa_column=Column(DECIMAL(15, 4 , asdecimal=False), nullable = False, server_default = "0.0"))
    discount_rate: float = Field(sa_column=Column(DECIMAL(15, 4 , asdecimal=False), nullable = False, server_default = "0.0"))
    description: str | None = Field(sa_column=Column(Text(), nullable = True))

class GeneralInvoiceItemORM(SQLModelWithSort, table=True):
    __tablename__ = "general_invoice_item"
    
    ginv_item_id: str = Field(
        sa_column=Column(String(length = 17), primary_key = True, nullable = False)
    )
    invoice_id: str = Field(
        sa_column=Column(
            String(length = 13), 
            ForeignKey(
                'invoice.invoice_id', 
                onupdate = 'CASCADE', 
                ondelete = 'CASCADE' # TODO
            ),
            primary_key = False, 
            nullable = False
        )
    )
    incur_dt: date = Field(sa_column=Column(Date(), nullable = False))
    acct_id: str = Field(
        sa_column=Column(
            String(length = 15), 
            ForeignKey(
                'accounts.acct_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            primary_key = False, 
            nullable = False
        )
    )
    currency: CurType | None = Field(
        sa_column=Column(ChoiceType(CurType, impl = Integer()), nullable = True)
    )
    amount_pre_tax_raw: float = Field(sa_column=Column(DECIMAL(15, 3 , asdecimal=False), nullable = False, server_default = "0.0"))
    amount_pre_tax: float = Field(sa_column=Column(DECIMAL(15, 3 , asdecimal=False), nullable = False, server_default = "0.0"))
    tax_rate: float = Field(sa_column=Column(DECIMAL(15, 4 , asdecimal=False), nullable = False, server_default = "0.0"))
    description: str | None = Field(sa_column=Column(Text(), nullable = True))
    

class ExpenseORM(SQLModelWithSort, table=True):
    __tablename__ = "expense"
    
    expense_id: str = Field(
        sa_column=Column(String(length = 15), primary_key = True, nullable = False)
    )
    expense_dt: date = Field(sa_column=Column(Date(), nullable = False))
    currency: CurType | None = Field(
        sa_column=Column(ChoiceType(CurType, impl = Integer()), nullable = True)
    )
    payment_acct_id: str = Field(
        sa_column=Column(
            String(length = 15), 
            ForeignKey(
                'accounts.acct_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            primary_key = False, 
            nullable = False
        )
    )
    payment_amount: float = Field(sa_column=Column(DECIMAL(15, 3 , asdecimal=False), nullable = False, server_default = "0.0"))
    exp_info: dict = Field(sa_column=Column(JSON(), nullable = True))
    note: str | None = Field(sa_column=Column(Text(), nullable = True))
    receipts: list[str] | None = Field(sa_column=Column(JSON(), nullable = True))
    journal_id: str = Field(
        sa_column=Column(
            String(length = 20),
            ForeignKey(
                'journals.journal_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT' # TODO: review this
            ),
            primary_key = False, 
            nullable = False
        )
    ) # TODO: in dao, need to add journal (auto mode) first, then add expense
    
    
class ExpenseItemORM(SQLModelWithSort, table=True):
    __tablename__ = "expense_item"
    
    expense_item_id: str = Field(
        sa_column=Column(String(length = 20), primary_key = True, nullable = False)
    )
    expense_id: str = Field(
        sa_column=Column(
            String(length = 15), 
            ForeignKey(
                'expense.expense_id', 
                onupdate = 'CASCADE', 
                ondelete = 'CASCADE'  # TODO
            ),
            primary_key = False, 
            nullable = False
        )
    )
    expense_acct_id: str = Field(
        sa_column=Column(
            String(length = 15), 
            ForeignKey(
                'accounts.acct_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            primary_key = False, 
            nullable = False
        )
    )
    amount_pre_tax: float = Field(sa_column=Column(DECIMAL(15, 3 , asdecimal=False), nullable = False, server_default = "0.0"))
    tax_rate: float = Field(sa_column=Column(DECIMAL(15, 4 , asdecimal=False), nullable = False, server_default = "0.0"))
    description: str | None = Field(sa_column=Column(Text(), nullable = True))
    
class PaymentORM(SQLModelWithSort, table=True):
    __tablename__ = "payment"
    
    payment_id: str = Field(
        sa_column=Column(String(length = 15), primary_key = True, nullable = False)
    )
    payment_num: str = Field(
        sa_column=Column(String(length = 25), primary_key = False, nullable = False, unique = True)
    )
    payment_dt: date = Field(sa_column=Column(Date(), nullable = False))
    entity_type: EntityType = Field(
        sa_column=Column(ChoiceType(EntityType, impl = Integer()), nullable = False, primary_key = False)
    )
    payment_acct_id: str = Field(
        sa_column=Column(
            String(length = 15), 
            ForeignKey(
                'accounts.acct_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            primary_key = False, 
            nullable = False
        )
    )
    journal_id: str = Field(
        sa_column=Column(
            String(length = 20),
            ForeignKey(
                'journals.journal_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT' # TODO: review this
            ),
            primary_key = False, 
            nullable = False
        )
    ) # TODO: in dao, need to add journal (auto mode) first, then add invoice
    payment_fee: float = Field(sa_column=Column(DECIMAL(15, 3 , asdecimal=False), nullable = False, server_default = "0.0"))
    ref_num: str | None = Field(sa_column=Column(Text(), nullable = True))
    note: str | None = Field(sa_column=Column(Text(), nullable = True))
    
class PaymentItemORM(SQLModelWithSort, table=True):
    __tablename__ = "payment_item"
    
    payment_item_id: str = Field(
        sa_column=Column(String(length = 18), primary_key = True, nullable = False)
    )
    payment_id: str = Field(
        sa_column=Column(
            String(length = 15), 
            ForeignKey(
                'payment.payment_id', 
                onupdate = 'CASCADE', 
                ondelete = 'CASCADE' # TODO
            ),
            primary_key = False, 
            nullable = False
        )
    )
    invoice_id: str = Field(
        sa_column=Column(
            String(length = 13), 
            ForeignKey(
                'invoice.invoice_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT' # TODO
            ),
            primary_key = False, 
            nullable = False
        )
    )
    payment_amount: float = Field(sa_column=Column(DECIMAL(15, 3 , asdecimal=False), nullable = False, server_default = "0.0"))
    payment_amount_raw: float = Field(sa_column=Column(DECIMAL(15, 3 , asdecimal=False), nullable = False, server_default = "0.0"))
    
    
class PropertyORM(SQLModelWithSort, table=True):
    __tablename__ = "property"
    
    property_id: str = Field(
        sa_column=Column(String(length = 14), primary_key = True, nullable = False)
    )
    property_name: str = Field(
        sa_column=Column(String(length = 50), nullable = False, unique = False)
    )
    property_type: PropertyType = Field(
        sa_column=Column(ChoiceType(PropertyType, impl = Integer()), nullable = False, primary_key = False)
    )
    pur_dt: date = Field(sa_column=Column(Date(), nullable = False))
    pur_price: float = Field(sa_column=Column(DECIMAL(15, 3 , asdecimal=False), nullable = False, server_default = "0.0"))
    pur_acct_id: str = Field(
        sa_column=Column(
            String(length = 15), 
            ForeignKey(
                'accounts.acct_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            primary_key = False, 
            nullable = False
        )
    )
    journal_id: str = Field(
        sa_column=Column(
            String(length = 20),
            ForeignKey(
                'journals.journal_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT' # TODO: review this
            ),
            primary_key = False, 
            nullable = False
        )
    )
    
class PropertyTransactionORM(SQLModelWithSort, table=True):
    __tablename__ = "property_trans"
    
    trans_id: str = Field(
        sa_column=Column(String(length = 18), primary_key = True, nullable = False)
    )
    property_id: str = Field(
        sa_column=Column(
            String(length = 14), 
            ForeignKey(
                'property.property_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT'
            ),
            primary_key = False, 
            nullable = False
        )
    )
    trans_dt: date = Field(sa_column=Column(Date(), nullable = False))
    trans_type: PropertyTransactionType = Field(
        sa_column=Column(ChoiceType(PropertyTransactionType, impl = Integer()), nullable = False, primary_key = False)
    )
    trans_amount: float = Field(sa_column=Column(DECIMAL(15, 3 , asdecimal=False), nullable = False, server_default = "0.0"))
    journal_id: str = Field(
        sa_column=Column(
            String(length = 20),
            ForeignKey(
                'journals.journal_id', 
                onupdate = 'CASCADE', 
                ondelete = 'RESTRICT' # TODO: review this
            ),
            primary_key = False, 
            nullable = False
        )
    )