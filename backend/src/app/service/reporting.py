
from datetime import date
from src.app.utils.tools import get_base_cur
from src.app.model.const import SystemAcctNumber
from src.app.model.exceptions import NotMatchWithSystemError
from src.app.model.journal import _AcctFlowAGG
from src.app.service.journal import JournalService
from src.app.service.acct import AcctService
from src.app.model.enums import AcctType

def get_acct_details(tree: dict, balances: dict[str, _AcctFlowAGG], bal_type: bool):
    accts = AcctService.get_accounts_by_chart(
        AcctService.get_chart(tree['chart_id'])
    )
    # extract necessary columns + extract balance
    acct_enriched = []
    for a in accts:
        r = {
            'acct_id': a.acct_id,
            'acct_name': a.acct_name
        }
        # fill with 0 if not found
        r['net_base'] = balances.get(a.acct_id, _AcctFlowAGG(acct_type=a.acct_type)).net_base
        
        # only add if balance sheet
        if bal_type:
            r['currency'] = a.currency
            r['net_raw'] = balances.get(a.acct_id, _AcctFlowAGG(acct_type=a.acct_type)).net_raw

        acct_enriched.append(r)
    
    # add to tree dict
    tree['acct_summary'] = acct_enriched
    
    # add chart aggregate sum
    net_base = sum(a['net_base'] for a in acct_enriched) # only need base amount
    
    if 'children' in tree:
        enriched_children = []
        for child in tree['children']:
            # add enriched child back
            child_details = get_acct_details(child, balances, bal_type)
            enriched_children.append(child_details)
            # add child chart summary to parent chart summary
            net_base += child_details['chart_summary']['net_base']

        tree['children'] = enriched_children
        
    tree['chart_summary'] = {
        'net_base': net_base
    }
    
    return tree


class ReportingService:
    
    @classmethod
    def get_balance_sheet_tree(cls, rep_dt: date) -> dict[AcctType, dict]:
        # get balances per acct id
        balances = JournalService.get_blsh_balances(rep_dt)
        
        bal_sh_tree = dict()
        for acct_type in (AcctType.AST, AcctType.LIB, AcctType.EQU):
            # get skeleton, i.e., the chart of account tree
            coa = AcctService.export_coa(acct_type=acct_type, simple=True)
            acct_details = get_acct_details(tree=coa, balances=balances, bal_type=True)
            bal_sh_tree[acct_type] = acct_details
            
        # need to calculate earnings from income statement on the fly
        # there is no earnings account defined, will be calculated here
        inc_exp_summary = JournalService.get_incexp_flows(date(1900, 1, 1), rep_dt)
        inc_total = sum(r.net_base for i, r in inc_exp_summary.items() if r.acct_type == AcctType.INC)
        exp_total = sum(r.net_base for i, r in inc_exp_summary.items() if r.acct_type == AcctType.EXP)
        re_total = inc_total - exp_total
        re_summary = {
            "acct_id": SystemAcctNumber.RETAIN_EARN, # excluding dividend
            "acct_name": "Retained Earnings (Excl. Div)",
            "net_base": re_total,
            "currency": get_base_cur(),
            "net_raw": re_total
        }
        
        # add retained earnings to the equity branch
        bal_sh_tree[AcctType.EQU]['acct_summary'].append(re_summary)
        # update chart summary for equity branch
        bal_sh_tree[AcctType.EQU]['chart_summary']['net_base'] += re_total
        
        return bal_sh_tree
        
    @classmethod
    def get_income_statment_tree(cls, start_dt: date, end_dt: date) -> dict[AcctType, dict]:
        # get income statment per acct id
        balances = JournalService.get_incexp_flows(start_dt, end_dt)
        
        inc_stat_tree = dict()
        for acct_type in (AcctType.INC, AcctType.EXP):
            # get skeleton, i.e., the chart of account tree
            coa = AcctService.export_coa(acct_type=acct_type, simple=True)
            acct_details = get_acct_details(tree=coa, balances=balances, bal_type=False)
            inc_stat_tree[acct_type] = acct_details
            
        return inc_stat_tree