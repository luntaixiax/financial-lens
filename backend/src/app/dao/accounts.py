import logging
from sqlmodel import Session, select
from sqlalchemy.exc import NoResultFound
from anytree import PreOrderIter, RenderTree
from src.app.model.enums import AcctType
from src.app.model.entity import BankAcct
from src.app.model.accounts import Account, Chart, ChartNode
from src.app.dao.orm import ChartOfAccountORM, AcctORM, BankAcctORM
from src.app.dao.connection import engine

class chartOfAcctDao:
    @classmethod
    def save(cls, top_node: ChartNode):
        # save the whole tree to DB
        logging.info("Saving following Chart of Accounts:\n")
        for pre, fill, node in RenderTree(top_node):
            logging.info("%s%s" % (pre, node.name))
    
        with Session(engine) as s:
            for node in PreOrderIter(top_node):
                # get parent id
                parent_chart_id = None
                if node.parent:
                    # if has parent, not root node
                    parent_chart_id = node.parent.chart.chart_id
                
                # whether the node already exist in the db
                sql = select(ChartOfAccountORM).where(
                    ChartOfAccountORM.chart_id == node.chart.chart_id
                )
                try:
                    old_node_orm = s.exec(sql).one()
                except NoResultFound:
                    # no existing node exist, will create one
                    new_node_orm = ChartOfAccountORM(
                        chart_id = node.chart.chart_id,
                        node_name = node.chart.name,
                        acct_type = node.chart.acct_type,
                        parent_chart_id = parent_chart_id
                    )
                    s.add(new_node_orm)
                    s.commit()
                else:
                    old_node_orm.node_name = node.chart.name
                    old_node_orm.acct_type = node.chart.acct_type
                    old_node_orm.parent_chart_id = parent_chart_id
                    s.add(old_node_orm)
                    s.commit()
                
    
    @classmethod
    def load(cls, acct_type: AcctType) -> ChartNode:
        # assemble the relevant tree from DB and return the top node
        with Session(engine) as s:
            def add_childs(node: ChartNode):
                # find child
                sql = select(ChartOfAccountORM).where(
                    ChartOfAccountORM.acct_type == acct_type,
                    ChartOfAccountORM.parent_chart_id == node.chart.chart_id
                )
                child_node_orms = s.exec(sql).all()
                for child_node_orm in child_node_orms:
                    # iterate over current child nodes
                    child_node = ChartNode(
                        chart = Chart(
                            chart_id = child_node_orm.chart_id,
                            name = child_node_orm.node_name,
                            acct_type = child_node_orm.acct_type,
                        ),
                        parent = node # link to current node
                    )
                    add_childs(child_node)
            
            # find root node
            # find immediate children node
            sql = select(ChartOfAccountORM).where(
                ChartOfAccountORM.acct_type == acct_type,
                ChartOfAccountORM.parent_chart_id == None
            )
            root_node_orm = s.exec(sql).one()
            root_node = ChartNode(
                chart = Chart(
                    chart_id = root_node_orm.chart_id,
                    name = root_node_orm.node_name,
                    acct_type = root_node_orm.acct_type,
                ),
                parent = None
            )
            
            # recursively add root node
            add_childs(root_node)
        
        return root_node # return root
            

class acctDao:
    @classmethod
    def fromAcct(cls, acct: Account) -> AcctORM:
        return AcctORM(
            acct_id=acct.acct_id,
            acct_name=acct.acct_name,
            acct_type=acct.acct_type,
            currency=acct.currency,
            chart_id=acct.chart.chart_id,
        )
        
    @classmethod
    def toAcct(cls, acct_orm: AcctORM, chart_orm: ChartOfAccountORM) -> Account:
        return Account(
            acct_id=acct_orm.acct_id,
            acct_name=acct_orm.acct_name,
            acct_type=acct_orm.acct_type,
            currency=acct_orm.currency,
            chart=Chart(
                chart_id=chart_orm.chart_id,
                name=chart_orm.node_name,
                acct_type=chart_orm.acct_type,
            )
            
        )
        
    @classmethod
    def add(cls, acct: Account):
        acct_orm = cls.fromAcct(acct)
        with Session(engine) as s:
            s.add(acct_orm)
            s.commit()
            logging.info(f"Added {acct_orm} to Account table")
            
    @classmethod
    def remove(cls, acct_id: str):
        with Session(engine) as s:
            sql = select(AcctORM).where(AcctORM.acct_id == acct_id)
            p = s.exec(sql).one() # get the ccount
            s.delete(p)
            s.commit()
            
        logging.info(f"Removed {p} from Account table")
        
    @classmethod
    def update(cls, acct: Account):
        acct_orm = cls.fromAcct(acct)
        with Session(engine) as s:
            sql = select(AcctORM).where(AcctORM.acct_id == acct_orm.acct_id)
            p = s.exec(sql).one() # get the accountluntaixia
            
            
            # update
            p.acct_name = acct_orm.acct_name
            p.acct_type = acct_orm.acct_type
            p.currency = acct_orm.currency
            p.chart_id = acct_orm.chart_id
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
        logging.info(f"Updated to {p} from Account table")
        
    @classmethod
    def get(cls, acct_id: str) -> Account:
        with Session(engine) as s:
            sql = select(AcctORM).where(AcctORM.acct_id == acct_id)
            acct_orm = s.exec(sql).one() # get the account
            
            # get chart orm
            sql = select(ChartOfAccountORM).where(
                ChartOfAccountORM.chart_id == acct_orm.chart_id
            )
            chart_orm = s.exec(sql).one() # get the account
            
        return cls.toAcct(acct_orm, chart_orm)


class bankAcctDao:
    @classmethod
    def fromAcct(cls, linked_acct_id: str, bank_acct: BankAcct) -> BankAcctORM:
        return BankAcctORM(
            linked_acct_id=linked_acct_id,
            **bank_acct.model_dump()
        )
        
    @classmethod
    def toAcct(cls, bank_acct_orm: BankAcctORM) -> BankAcct:
        return BankAcct.model_validate(
            bank_acct_orm.model_dump(exclude=['linked_acct_id'])
        )
        
    @classmethod
    def add(cls, linked_acct_id: str, acct: BankAcct):
        acct_orm = cls.fromAcct(linked_acct_id, acct)
        with Session(engine) as s:
            s.add(acct_orm)
            s.commit()
            logging.info(f"Added {acct_orm} to Bank Account table")
            
    @classmethod
    def remove(cls, linked_acct_id: str):
        with Session(engine) as s:
            sql = select(BankAcctORM).where(BankAcctORM.acct_id == linked_acct_id)
            p = s.exec(sql).one() # get the ccount
            s.delete(p)
            s.commit()
            
        logging.info(f"Removed {p} from Bank Account table")
        
    @classmethod
    def update(cls, linked_acct_id: str, acct: BankAcct):
        acct_orm = cls.fromAcct(linked_acct_id, acct)
        with Session(engine) as s:
            sql = select(BankAcctORM).where(
                BankAcctORM.linked_acct_id == acct_orm.linked_acct_id
            )
            p = s.exec(sql).one() # get the accountluntaixia
            
            
            # update
            p.bank_name = acct_orm.bank_name
            p.bank_acct_number = acct_orm.bank_acct_number
            p.bank_acct_type = acct_orm.bank_acct_type
            
            s.add(p)
            s.commit()
            s.refresh(p) # update p to instantly have new values
            
        logging.info(f"Updated to {p} from Bank Account table")
        
    @classmethod
    def get(cls, linked_acct_id: str) -> BankAcct:
        with Session(engine) as s:
            sql = select(BankAcctORM).where(
                BankAcctORM.linked_acct_id == linked_acct_id
            )
            p = s.exec(sql).one() # get the account
        return cls.toAcct(p)