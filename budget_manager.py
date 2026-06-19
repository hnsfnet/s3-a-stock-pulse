from datastore import DataStore
from datetime import datetime


class BudgetManager:
    WARNING_THRESHOLD = 0.8
    DANGER_THRESHOLD = 1.0

    def __init__(self, datastore: DataStore):
        self.ds = datastore

    def set_total_budget(self, year_month, amount):
        if amount < 0:
            raise ValueError('预算金额不能为负数')
        return self.ds.set_budget(year_month, amount, category_id=None)

    def set_category_budget(self, year_month, category_id, amount):
        if amount < 0:
            raise ValueError('预算金额不能为负数')
        return self.ds.set_budget(year_month, amount, category_id=category_id)

    def delete_budget(self, budget_id):
        return self.ds.delete_budget(budget_id)

    def get_budgets(self, year_month):
        return self.ds.get_budgets(year_month)

    def get_total_budget(self, year_month):
        budget = self.ds.get_budget(year_month, category_id=None)
        return budget['amount'] if budget else 0

    def get_category_budgets(self, year_month):
        budgets = self.ds.get_budgets(year_month)
        return [b for b in budgets if b['type'] == 'category']

    def get_total_budget_status(self, year_month):
        total_budget = self.get_total_budget(year_month)
        monthly_summary = self.ds.get_monthly_summary(year_month)
        total_expense = monthly_summary['total_expense']

        if total_budget == 0:
            ratio = 0
        else:
            ratio = total_expense / total_budget

        status = 'normal'
        if ratio >= self.DANGER_THRESHOLD:
            status = 'danger'
        elif ratio >= self.WARNING_THRESHOLD:
            status = 'warning'

        return {
            'budget': total_budget,
            'spent': total_expense,
            'remaining': total_budget - total_expense,
            'ratio': ratio,
            'status': status
        }

    def get_category_budget_status(self, year_month):
        category_expenses = self.ds.get_category_expense_summary(year_month)
        category_budgets = self.get_category_budgets(year_month)

        budget_map = {}
        for b in category_budgets:
            if b['category_id']:
                budget_map[b['category_id']] = b

        result = []
        for exp in category_expenses:
            budget = budget_map.get(exp['id'])
            budget_amount = budget['amount'] if budget else 0

            if budget_amount == 0:
                ratio = 0
            else:
                ratio = exp['total'] / budget_amount

            status = 'normal'
            if budget_amount > 0:
                if ratio >= self.DANGER_THRESHOLD:
                    status = 'danger'
                elif ratio >= self.WARNING_THRESHOLD:
                    status = 'warning'

            result.append({
                'category_id': exp['id'],
                'category_name': exp['name'],
                'category_icon': exp['icon'],
                'budget': budget_amount,
                'spent': exp['total'],
                'remaining': budget_amount - exp['total'],
                'ratio': ratio,
                'status': status
            })

        for b in category_budgets:
            if b['category_id'] and b['category_id'] not in [r['category_id'] for r in result]:
                result.append({
                    'category_id': b['category_id'],
                    'category_name': b['category_name'],
                    'category_icon': b['category_icon'],
                    'budget': b['amount'],
                    'spent': 0,
                    'remaining': b['amount'],
                    'ratio': 0,
                    'status': 'normal'
                })

        return result

    def get_warnings(self, year_month):
        warnings = []
        total_status = self.get_total_budget_status(year_month)
        if total_status['status'] != 'normal' and total_status['budget'] > 0:
            warnings.append({
                'type': 'total',
                'level': total_status['status'],
                'message': f'总预算已使用 {total_status["ratio"]*100:.1f}%，已支出 ¥{total_status["spent"]:.2f}'
            })

        category_statuses = self.get_category_budget_status(year_month)
        for cs in category_statuses:
            if cs['status'] != 'normal' and cs['budget'] > 0:
                warnings.append({
                    'type': 'category',
                    'category_id': cs['category_id'],
                    'category_name': cs['category_name'],
                    'level': cs['status'],
                    'message': f'{cs["category_name"]}预算已使用 {cs["ratio"]*100:.1f}%，已支出 ¥{cs["spent"]:.2f}'
                })

        return warnings

    def get_budget_remaining(self, year_month):
        total_status = self.get_total_budget_status(year_month)
        return total_status['remaining']

    def get_current_month_str(self):
        return datetime.now().strftime('%Y-%m')
