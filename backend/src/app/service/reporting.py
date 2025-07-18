
from datetime import date
from src.app.model.const import SystemAcctNumber
from src.app.model.journal import _AcctFlowAGG
from src.app.service.journal import JournalService
from src.app.service.acct import AcctService
from src.app.model.enums import AcctType
from src.app.service.settings import ConfigService


class ReportingService:
    
    def __init__(
        self, 
        journal_service: JournalService, 
        acct_service: AcctService, 
        setting_service: ConfigService
    ):
        self.journal_service = journal_service
        self.acct_service = acct_service
        self.setting_service = setting_service
        
    def get_acct_details(self, tree: dict, balances: dict[str, _AcctFlowAGG], bal_type: bool):
        accts = self.acct_service.get_accounts_by_chart(
            self.acct_service.get_chart(tree['chart_id'])
        )
        # extract necessary columns + extract balance
        acct_enriched = []
        for a in accts:
            r = {
                'acct_id': a.acct_id,
                'acct_name': a.acct_name
            }
            # fill with 0 if not found
            r['net_base'] = balances.get(a.acct_id, _AcctFlowAGG(acct_type=a.acct_type)).net_base # type: ignore
            
            # only add if balance sheet
            if bal_type:
                r['currency'] = a.currency # type: ignore
                r['net_raw'] = balances.get(a.acct_id, _AcctFlowAGG(acct_type=a.acct_type)).net_raw # type: ignore

            acct_enriched.append(r)
        
        # add to tree dict
        tree['acct_summary'] = acct_enriched
        
        # add chart aggregate sum
        net_base = sum(a['net_base'] for a in acct_enriched) # only need base amount
        
        if 'children' in tree:
            enriched_children = []
            for child in tree['children']:
                # add enriched child back
                child_details = self.get_acct_details(child, balances, bal_type)
                enriched_children.append(child_details)
                # add child chart summary to parent chart summary
                net_base += child_details['chart_summary']['net_base']

            tree['children'] = enriched_children
            
        tree['chart_summary'] = {
            'net_base': net_base
        }
        
        return tree
    
    def get_balance_sheet_tree(self, rep_dt: date) -> dict[AcctType, dict]:
        base_cur =  self.setting_service.get_base_currency()
        # get balances per acct id
        balances = self.journal_service.get_blsh_balances(rep_dt)
        
        bal_sh_tree = dict()
        for acct_type in (AcctType.AST, AcctType.LIB, AcctType.EQU):
            # get skeleton, i.e., the chart of account tree
            coa = self.acct_service.export_coa(acct_type=acct_type, simple=True)
            acct_details = self.get_acct_details(tree=coa, balances=balances, bal_type=True)
            bal_sh_tree[acct_type] = acct_details
            
        # need to calculate earnings from income statement on the fly
        # there is no earnings account defined, will be calculated here
        inc_exp_summary = self.journal_service.get_incexp_flows(date(1900, 1, 1), rep_dt)
        inc_total = sum(r.net_base for i, r in inc_exp_summary.items() if r.acct_type == AcctType.INC) # type: ignore
        exp_total = sum(r.net_base for i, r in inc_exp_summary.items() if r.acct_type == AcctType.EXP) # type: ignore
        re_total = inc_total - exp_total
        re_summary = {
            "acct_id": SystemAcctNumber.RETAIN_EARN, # excluding dividend
            "acct_name": "Retained Earnings (Excl. Div)",
            "net_base": re_total,
            "currency": base_cur,
            "net_raw": re_total
        }
        
        # add retained earnings to the equity branch
        bal_sh_tree[AcctType.EQU]['acct_summary'].append(re_summary)
        # update chart summary for equity branch
        bal_sh_tree[AcctType.EQU]['chart_summary']['net_base'] += re_total
        
        return bal_sh_tree
        
    def get_income_statment_tree(self, start_dt: date, end_dt: date) -> dict[AcctType, dict]:
        # get income statment per acct id
        balances = self.journal_service.get_incexp_flows(start_dt, end_dt)
        
        inc_stat_tree = dict()
        for acct_type in (AcctType.INC, AcctType.EXP):
            # get skeleton, i.e., the chart of account tree
            coa = self.acct_service.export_coa(acct_type=acct_type, simple=True)
            acct_details = self.get_acct_details(tree=coa, balances=balances, bal_type=False)
            inc_stat_tree[acct_type] = acct_details
            
        return inc_stat_tree