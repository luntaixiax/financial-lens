import logging
from sqlmodel import Session, select, delete, col
from sqlalchemy.exc import NoResultFound, IntegrityError
from anytree import PreOrderIter
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError
from src.app.model.enums import AcctType
from src.app.model.accounts import Account, Chart, ChartNode
from src.app.dao.orm import ChartOfAccountORM, AcctORM, infer_integrity_error
from src.app.dao.connection import get_engine

class chartOfAcctDao:
    @classmethod
    def save(cls, top_node: ChartNode):
        # save the whole tree to DB
        logging.info("Saving following Chart of Accounts:\n")
        top_node.print()
            
        # get existing nodes for extra node deletion below
        try:
            existing_node = cls.load(top_node.chart.acct_type)
        except NotExistError:
            ordered_nodes = [] # no existing node
        else:
            # get the order of chart ids in case need to delete
            ordered_nodes = list(existing_node.descendants)[::-1] + [existing_node]
    
        with Session(get_engine()) as s:
            # get already existing nodes within same chart type in db
            sql = select(ChartOfAccountORM.chart_id).where(
                ChartOfAccountORM.acct_type == top_node.chart.acct_type,
            )
            db_chart_ids = s.exec(sql).all()
            
            # for nodes that already exist and newly created in the given node
            kept_chart_ids = []
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
                    # add existing node to seen nodes
                    kept_chart_ids.append(node.chart.chart_id)
                    
            # but also need to remove nodes that be "deleted" -- in db but not in top_node (within same chart type)
            chart_ids_to_rm = list(set(db_chart_ids).difference(kept_chart_ids))
            logging.info(f"Chart ids ({top_node.chart.acct_type}) in db before update: {db_chart_ids}, need to drop: {chart_ids_to_rm}")
            
            if len(chart_ids_to_rm) > 0:
                # need to delete by bottom to top order, otherwise will have FK error
                for node in ordered_nodes:
                    if node.chart.chart_id in chart_ids_to_rm:
                        sql = select(ChartOfAccountORM).where(
                            ChartOfAccountORM.chart_id == node.chart_id
                        )
                        p = s.exec(sql).one() # get the chart of account
                        s.delete(p)
            
            try:
                s.commit() # submit all in one commit
            except IntegrityError as e:
                s.rollback()
                # if error, can only be the following scenario:
                # the chart to remove have another chart / account belongs to it (FK on delete) 
                raise FKNoDeleteUpdateError(details=str(e))
                
    
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
            try:
                root_node_orm = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e)) # top node not exist
                
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
        
    @classmethod
    def remove(cls, acct_type: AcctType):
        # remove all charts under same acct type
        try:
            top_node = cls.load(acct_type)
        except NotExistError as e:
            return
            
        with Session(get_engine()) as s:
            # need to delete from bottom node to top node
            for node in list(top_node.descendants)[::-1] + [top_node]:
                sql = select(ChartOfAccountORM).where(
                    ChartOfAccountORM.chart_id == node.chart_id
                )
                p = s.exec(sql).one() # get the chart of account
                
                # need to delete (commit) one at a time
                # because there are FK on same column
                try:
                    s.delete(p)
                    s.commit() # submit all in one commit
                except IntegrityError as e:
                    s.rollback()
                    # if error, can only be the following scenario:
                    # the chart to remove have another chart / account belongs to it (FK on delete) 
                    raise FKNoDeleteUpdateError(details=str(e))
            
    @classmethod
    def toChart(cls, chart_orm: ChartOfAccountORM) -> Chart:
        return Chart(
            chart_id=chart_orm.chart_id,
            name=chart_orm.node_name,
            acct_type=chart_orm.acct_type,
        )

    @classmethod
    def get_chart(cls, chart_id: str) -> Chart:
        # get chart orm
        with Session(get_engine()) as s:
            sql = select(ChartOfAccountORM).where(
                ChartOfAccountORM.chart_id == chart_id
            )
            try:
                chart_orm = s.exec(sql).one() # get the account
            except NoResultFound as e:
                raise NotExistError(details=str(e))
        
        return cls.toChart(chart_orm)
    
    @classmethod
    def get_charts(cls, acct_type: AcctType) -> list[Chart]:
        # get chart orm
        with Session(get_engine()) as s:
            sql = select(ChartOfAccountORM).where(
                ChartOfAccountORM.acct_type == acct_type
            )
            try:
                chart_orms = s.exec(sql).all() # get the charts
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
        return [cls.toChart(chart_orm) for chart_orm in chart_orms]
    
    @classmethod
    def get_parent_chart(cls, chart_id: str) -> Chart:
        with Session(get_engine()) as s:
            sql = select(ChartOfAccountORM).where(
                ChartOfAccountORM.chart_id == (
                    select(ChartOfAccountORM.parent_chart_id)
                    .where(
                        ChartOfAccountORM.chart_id == chart_id
                    )
                )
            )
            
            try:
                chart_orm = s.exec(sql).one() # get the chart
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
        return cls.toChart(chart_orm)

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
    def toAcct(cls, acct_orm: AcctORM, chart: Chart) -> Account:
        return Account(
            acct_id=acct_orm.acct_id,
            acct_name=acct_orm.acct_name,
            acct_type=acct_orm.acct_type,
            currency=acct_orm.currency,
            chart=chart
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
                raise NotExistError(details=str(e))    
            
            try:
                s.delete(p)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise FKNoDeleteUpdateError(details=str(e))
            
            logging.info(f"Removed {p} from Account table")
        
    @classmethod
    def update(cls, acct: Account):
        acct_orm = cls.fromAcct(acct)
        with Session(get_engine()) as s:
            sql = select(AcctORM).where(AcctORM.acct_id == acct_orm.acct_id)
            try:
                p = s.exec(sql).one()
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            # update
            if not p == acct_orm:
                p.acct_name = acct_orm.acct_name
                p.acct_type = acct_orm.acct_type
                p.currency = acct_orm.currency
                p.chart_id = acct_orm.chart_id

                try:
                    s.add(p)
                    s.commit()
                except IntegrityError as e:
                    # if integrity error happened here, must certainly it is because
                    # updated chart_id does not exist
                    s.rollback()
                    raise FKNotExistError(details=str(e))
                else:
                    s.refresh(p) # update p to instantly have new values
                    logging.info(f"Updated to {p} from Account table")
        
    @classmethod
    def get_chart_id_by_acct(cls, acct_id: str) -> str:
        with Session(get_engine()) as s:
            sql = select(AcctORM.chart_id).where(
                AcctORM.acct_id == acct_id
            )
            try:
                chart_id = s.exec(sql).one() # get the account
            except NoResultFound as e:
                raise NotExistError(details=str(e))
        return chart_id
    
    @classmethod
    def get(cls, acct_id: str, chart: Chart) -> Account:
        with Session(get_engine()) as s:
            sql = select(AcctORM).where(AcctORM.acct_id == acct_id)
            try:
                acct_orm = s.exec(sql).one() # get the account
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
        return cls.toAcct(acct_orm, chart)
    
    @classmethod
    def get_accts_by_chart(cls, chart: Chart) -> list[Account]:
        with Session(get_engine()) as s:
            sql = select(AcctORM).where(
                AcctORM.chart_id == chart.chart_id
            )
            try:
                acct_orms = s.exec(sql).all() # get the accounts
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
        return [cls.toAcct(acct_orm, chart) for acct_orm in acct_orms]