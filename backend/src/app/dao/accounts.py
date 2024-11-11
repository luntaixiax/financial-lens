import logging
from sqlmodel import Session, select
from sqlalchemy.exc import NoResultFound, IntegrityError
from anytree import PreOrderIter, RenderTree
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, NotExistError
from src.app.model.enums import AcctType
from src.app.model.accounts import Account, Chart, ChartNode
from src.app.dao.orm import ChartOfAccountORM, AcctORM, infer_integrity_error
from src.app.dao.connection import get_engine

class chartOfAcctDao:
    @classmethod
    def save(cls, top_node: ChartNode):
        # save the whole tree to DB
        logging.info("Saving following Chart of Accounts:\n")
        for pre, fill, node in RenderTree(top_node):
            logging.info("%s%s" % (pre, node.name))
    
        with Session(get_engine()) as s:
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
                    
                else:
                    # otherwise update the nodes
                    old_node_orm.node_name = node.chart.name
                    old_node_orm.acct_type = node.chart.acct_type
                    old_node_orm.parent_chart_id = parent_chart_id
                    s.add(old_node_orm)
            
            try:
                s.commit() # submit all in one commit
            except IntegrityError as e:
                s.rollback()
                raise AlreadyExistError(e)
                
    
    @classmethod
    def load(cls, acct_type: AcctType) -> ChartNode:
        # assemble the relevant tree from DB and return the top node
        with Session(get_engine()) as s:
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
        with Session(get_engine()) as s:
            s.add(acct_orm)
            
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise infer_integrity_error(e, during_creation=True)
            else:
                logging.info(f"Added {acct_orm} to Account table")
            
    @classmethod
    def remove(cls, acct_id: str):
        with Session(get_engine()) as s:
            sql = select(AcctORM).where(AcctORM.acct_id == acct_id)
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(f"Account not found: {acct_id}")    
            
            try:
                s.delete(p)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNoDeleteUpdateError(f"acct {acct_id} referenced in some table")
            
            logging.info(f"Removed {p} from Account table")
        
    @classmethod
    def update(cls, acct: Account):
        acct_orm = cls.fromAcct(acct)
        with Session(get_engine()) as s:
            sql = select(AcctORM).where(AcctORM.acct_id == acct_orm.acct_id)
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(f"Account not found: {acct.acct_id}")
            
            # update
            if not p == acct_orm:
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
        with Session(get_engine()) as s:
            sql = select(AcctORM).where(AcctORM.acct_id == acct_id)
            try:
                acct_orm = s.exec(sql).one() # get the account
            except NoResultFound as e:
                raise NotExistError(f"Account not found: {acct_id}")
            
            # get chart orm
            sql = select(ChartOfAccountORM).where(
                ChartOfAccountORM.chart_id == acct_orm.chart_id
            )
            try:
                chart_orm = s.exec(sql).one() # get the account
            except NoResultFound as e:
                raise NotExistError(f"Chart not found: {acct_orm.chart_id}")
            
        return cls.toAcct(acct_orm, chart_orm)