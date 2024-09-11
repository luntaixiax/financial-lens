from dacite import from_dict, Config
from enum import Enum
from pydantic import BaseModel
from fastapi import File, FastAPI
from typing import Tuple, List, Dict, Any
from datetime import date, datetime
from model.entity import Entity
from model.accounts import BalSh, IncExp
from model.transactions import Transaction, Entry
from model.invoice import Invoice
from model.enums import CurType
from service.entity_manager import EntityManager
from service.acct_manager import AcctManager
from service.transaction_manager import TransManager
from service.invoice_manager import InvoiceManager
from service.fx_manager import FxManager
from utils.tools import id_generator


app = FastAPI() # instantiate

@app.put("/entity/create")
def create_entity(entity: Entity) -> str:
    entity_id = id_generator(prefix = 'e-', length = 5)
    # map parameters to Model
    entity.entity_id = entity_id
    # send Model to service
    EntityManager.create(entity = entity)
    
    return entity_id

@app.post("/entity/update")
def update_entity(entity_id: str, entity: Entity):
    # map parameters to Model
    entity.entity_id = entity_id
    
    # send Model to service
    EntityManager.update(entity = entity)
    
@app.delete("/entity/delete")
def delete_entity(entity_id: str):
    EntityManager.delete(entity_id = entity_id)

@app.put("/account/balsh/create")
def create_balsh_acct(acct: BalSh) -> str:
    acct_id = id_generator(prefix = 'a-', length = 6)
    # map parameters to Model
    acct.acct_id = acct_id
    # send Model to service
    AcctManager.createBalsh(acct = acct)
    
    return acct_id
    
@app.post("/account/balsh/update")
def update_balsh_acct(acct_id: str, acct: BalSh):
    # map parameters to Model
    acct.acct_id = acct_id
    
    # send Model to service
    AcctManager.updateBalsh(acct = acct)
    
@app.delete("/account/balsh/delete")
def delete_balsh_acct(acct_id: str):
    AcctManager.deleteBalsh(acct_id = acct_id)
    
    
@app.put("/account/incexp/create")
def create_incexp_acct(acct: IncExp) -> str:
    acct_id = id_generator(prefix = 'a-', length = 6)
    # map parameters to Model
    acct.acct_id = acct_id
    # send Model to service
    AcctManager.createIncExp(acct = acct)
    
    return acct_id
    
@app.post("/account/incexp/update")
def update_incexp_acct(acct_id: str, acct: IncExp):
    # map parameters to Model
    acct.acct_id = acct_id
    
    # send Model to service
    AcctManager.updateIncExp(acct = acct)
    
@app.delete("/account/incexp/delete")
def delete_incexp_acct(acct_id: str):
    AcctManager.deleteIncExp(acct_id = acct_id)
    
@app.put("/transaction/create")
def create_transaction(transaction: Transaction) -> str:
    trans_id = id_generator(prefix = 't-', length = 13)
    # map parameters to Model
    transaction.trans_id = trans_id
    # add entry id
    for entry in transaction.entries:
        entry.entry_id = id_generator(prefix = 'et-', length = 17)
    # send Model to service
    TransManager.create(transaction=transaction)
    
    return trans_id

@app.post("/transaction/update")
def update_transaction(trans_id: str, transaction: Transaction):
    # the transaction can have no trans_id
    # existing entry must have entry_id
    # new entry can have null entry_id
    
    # check entry id, add if not any
    # add entry id
    for entry in transaction.entries:
        if entry.entry_id is None:
            # must be new entry
            entry.entry_id = id_generator(prefix = 'et-', length = 17)
    
    # map parameters to Model
    transaction.trans_id = trans_id
    # send Model to service
    TransManager.update(transaction = transaction)
    
@app.delete("/transaction/delete")
def delete_transaction(trans_id: str):
    TransManager.delete(trans_id=trans_id)
    
    
@app.put("/invoice/create")
def create_invoice(invoice: Invoice) -> str:
    invoice_id = id_generator(prefix = 'i-', length = 13)
    # map parameters to Model
    invoice.invoice_id = invoice_id
    # send Model to service
    InvoiceManager.create(invoice = invoice)
    
    return invoice_id

@app.put("/invoice/create_pdf")
def create_invoice_pdf(invoice_id: str, size: Tuple[int] | Any = (650, 800)):
    # get invoice
    invoice = InvoiceManager.get(invoice_id=invoice_id)
    # create pdf
    InvoiceManager.make_pdf_invoice(
        invoice = invoice,
        size = size
    )

@app.post("/invoice/update")
def update_invoice(invoice_id: str, invoice: Invoice):
    # map parameters to Model
    invoice.invoice_id = invoice_id
    
    # send Model to service
    InvoiceManager.update(invoice = invoice)
    
@app.delete("/invoice/delete")
def delete_invoice(invoice_id: str):
    InvoiceManager.delete(invoice_id = invoice_id)
    
@app.post("/fx/pull")
def pull_fx(cur_dt: date, overwrite: bool = False):
    FxManager.pull(
        cur_dt=cur_dt,
        overwrite=overwrite
    )
    
@app.get("/fx/get")
def get_fx(currency: CurType, cur_dt: date) -> float:
    return FxManager.get(
        cur_dt=cur_dt,
        currency=currency
    )
    
if __name__ == '__main__':
    # from model.enums import IncExpType
    
    # for acct_name in [
    #     # home related
    #     'Rent',
    #     'Property Tax',
    #     'MTG Int', # mortgage interest
    #     'Mgmt Fee',
    #     'Insurance',
    #     'Utility',
    #     'Telecom',
    #     # food related
    #     'Dine Out',
    #     'Grocery',
    #     'Snack',
    #     'Drink',
    #     # fixture related
    #     'Electronics',
    #     'Furnature',
    #     'Home Supplier ',
    #     'Pets',
    #     # transport related
    #     'Taxi',
    #     'Train',
    #     'Public Transport',
    #     'Gas',
    #     'Parking',
    #     # education related
    #     'Tuition',
    #     'Book',
    #     # shopping related
    #     'Clothes',
    #     'Shoes',
    #     'Jewellery',
    #     'Game & Toy',
    #     # health related
    #     'Drug',
    #     'Sport',
    #     'Fashion',
    #     # entertainment & service
    #     'Movie',
    #     'Membership',
    #     '3rd Service',
    #     'Entertain',
    #     'Delivery',
    #     # social related
    #     'Treat',
    #     'Gift',
    #     'Red Packet',
    #     # travel related
    #     'Ferry',
    #     'Airline',
    #     'Hotel',
    #     'Ticket',
    #     # investment related
    #     'Interest Exp',
    #     'Realized Loss',
    #     'Unrealized Loss',
    #     'Unexpected Loss'
    # ]:
    #     create_incexp_acct(
    #         acct = IncExp(
    #             acct_name = acct_name,
    #             entity_id = 'e-a998a',
    #             acct_type = IncExpType.EXP
    #         )
    #     )
        
    # for acct_name in [
    #     # career related
    #     'Salary',
    #     'Commision',
    #     'Subsidy',
    #     'Bonus',
    #     # investment related
    #     'Interest Inc',
    #     'Dividend',
    #     'Rental',
    #     'Unrealizd Gain',
    #     'Realized Gain',
    #     # other
    #     'Refund',
    #     'Green Packet',
    #     'Pension',
    #     'Unexpected Gain'
    # ]:
    #     create_incexp_acct(
    #         acct = IncExp(
    #             acct_name = acct_name,
    #             entity_id = 'e-a998a',
    #             acct_type = IncExpType.INC
    #         )
    #     )
        
        
    # {
    #     "trans_dt": "2023-10-19T01:45:21.803Z",
    #     "entity_id": "e-a998a",
    #     "entries": [
    #         {
    #         "entry_type": 1,
    #         "acct_id_balsh": "a-2a81cd",
    #         "acct_id_incexp": None,
    #         "incexp_cur": None,
    #         "amount": 150,
    #         "event": 1,
    #         "project": "daily"
    #         },
    #         {
    #         "entry_type": 2,
    #         "acct_id_balsh": None,
    #         "acct_id_incexp": "a-67e7c0",
    #         "incexp_cur": 2,
    #         "amount": 150,
    #         "event": 1,
    #         "project": "daily"
    #         }
    #     ],
    #     "note": "dine out at KFC"
    # }
    from utils.tools import get_settings
    
    ll = get_settings()
    print(ll)