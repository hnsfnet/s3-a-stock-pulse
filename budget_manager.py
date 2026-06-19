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

    def _calc_status(self, ratio, budget_amount):
        if budget_amount == 0:
            return 'normal'
        if ratio >= self.DANGER_THRESHOLD:
            return 'danger'
        elif ratio >= self.WARNING_THRESHOLD:
            return 'warning'
        return 'normal'

    def get_category_budget_status(self, year_month):
        return self.get_category_budget_status_tree(year_month)

    def get_category_budget_status_tree(self, year_month):
        expense_data = self.ds.get_category_expense_summary(year_month)
        category_budgets = self.ds.get_budgets(year_month)
        expense_categories = self.ds.get_categories('expense', parent_only=True)
        all_subcategories = {}
        for parent in expense_categories:
            all_subcategories[parent['id']] = self.ds.get_subcategories(parent['id'])

        budget_map = {}
        for b in category_budgets:
            if b['category_id']:
                budget_map[b['category_id']] = b

        expense_map = {}
        for exp in expense_data:
            expense_map[exp['id']] = exp['total']

        result = []
        for parent in expense_categories:
            pid = parent['id']
            parent_budget = budget_map.get(pid)
            parent_budget_amount = parent_budget['amount'] if parent_budget else 0
            parent_direct_spent = expense_map.get(pid, 0)

            children_status = []
            children_total_spent = 0
            for sub in all_subcategories.get(pid, []):
                sid = sub['id']
                sub_budget = budget_map.get(sid)
                sub_budget_amount = sub_budget['amount'] if sub_budget else 0
                sub_spent = expense_map.get(sid, 0)
                children_total_spent += sub_spent

                sub_ratio = sub_spent / sub_budget_amount if sub_budget_amount > 0 else 0
                sub_status = self._calc_status(sub_ratio, sub_budget_amount)

                children_status.append({
                    'category_id': sid,
                    'category_name': sub['name'],
                    'category_icon': sub['icon'],
                    'parent_id': pid,
                    'budget': sub_budget_amount,
                    'spent': sub_spent,
                    'remaining': sub_budget_amount - sub_spent,
                    'ratio': sub_ratio,
                    'status': sub_status
                })

            total_spent = parent_direct_spent + children_total_spent
            ratio = total_spent / parent_budget_amount if parent_budget_amount > 0 else 0
            status = self._calc_status(ratio, parent_budget_amount)

            result.append({
                'category_id': pid,
                'category_name': parent['name'],
                'category_icon': parent['icon'],
                'parent_id': None,
                'budget': parent_budget_amount,
                'spent': total_spent,
                'direct_spent': parent_direct_spent,
                'remaining': parent_budget_amount - total_spent,
                'ratio': ratio,
                'status': status,
                'children': children_status
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

        tree = self.get_category_budget_status_tree(year_month)
        for parent in tree:
            if parent['status'] != 'normal' and parent['budget'] > 0:
                warnings.append({
                    'type': 'category',
                    'category_id': parent['category_id'],
                    'category_name': parent['category_name'],
                    'level': parent['status'],
                    'message': f'{parent["category_name"]}预算已使用 {parent["ratio"]*100:.1f}%，已支出 ¥{parent["spent"]:.2f}'
                })
            for child in parent.get('children', []):
                if child['status'] != 'normal' and child['budget'] > 0:
                    warnings.append({
                        'type': 'subcategory',
                        'category_id': child['category_id'],
                        'category_name': f'{parent["category_name"]} > {child["category_name"]}',
                        'level': child['status'],
                        'message': f'{parent["category_name"]} > {child["category_name"]}预算已使用 {child["ratio"]*100:.1f}%，已支出 ¥{child["spent"]:.2f}'
                    })

        return warnings

    def get_budget_remaining(self, year_month):
        total_status = self.get_total_budget_status(year_month)
        return total_status['remaining']

    def get_current_month_str(self):
        return datetime.now().strftime('%Y-%m')
