from datetime import date
from database import DatabaseConnection
from repositories import TransactionRepository, BudgetRepository, CategoryRepository


class BudgetManager:
    WARNING_THRESHOLD = 0.8
    DANGER_THRESHOLD = 1.0

    def __init__(self, ledger_or_ds=None, db=None):
        if ledger_or_ds is not None and hasattr(ledger_or_ds, '_tx_repo'):
            ledger = ledger_or_ds
            self._tx_repo = ledger._tx_repo
            self._budget_repo = ledger._budget_repo
            self._cat_repo = ledger._cat_repo
            self.ds = None
        elif ledger_or_ds is not None and hasattr(ledger_or_ds, '_tx'):
            ds = ledger_or_ds
            self._tx_repo = ds._tx
            self._budget_repo = ds._budget
            self._cat_repo = ds._cat
            self.ds = _DSCompatAdapter(self._tx_repo, self._budget_repo, self._cat_repo)
        else:
            self._tx_repo = TransactionRepository(db)
            self._budget_repo = BudgetRepository(db)
            self._cat_repo = CategoryRepository(db)
            self.ds = _DSCompatAdapter(self._tx_repo, self._budget_repo, self._cat_repo)

    def get_current_month_str(self):
        return date.today().strftime('%Y-%m')

    def set_total_budget(self, year_month, amount):
        self._budget_repo.set(year_month, amount, category_id=None)

    def set_category_budget(self, year_month, category_id, amount):
        self._budget_repo.set(year_month, amount, category_id=category_id)

    def get_total_budget(self, year_month):
        b = self._budget_repo.get(year_month, category_id=None)
        return float(b['amount']) if b and b.get('amount') else 0.0

    def get_category_budgets(self, year_month):
        all_b = self._budget_repo.get_all(year_month)
        return [b for b in all_b if b.get('category_id') is not None]

    def get_total_budget_status(self, year_month):
        total_budget = self.get_total_budget(year_month)
        monthly_summary = self._tx_repo.get_monthly_summary(year_month)
        total_expense = monthly_summary['total_expense']

        if not isinstance(total_expense, (int, float)) or total_expense < 0:
            total_expense = 0.0
        if total_budget < 0:
            total_budget = 0.0

        if total_budget == 0:
            ratio = 0
        else:
            ratio = min(total_expense / total_budget, 10.0)

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

    def _calc_status(self, ratio, has_budget):
        if not has_budget:
            return 'none'
        if ratio >= self.DANGER_THRESHOLD:
            return 'danger'
        elif ratio >= self.WARNING_THRESHOLD:
            return 'warning'
        return 'normal'

    def get_category_budget_status(self, year_month, category_id):
        b = self._budget_repo.get(year_month, category_id=category_id)
        budget = float(b['amount']) if b and b.get('amount') else 0.0
        expenses = self._tx_repo.get_category_expense_summary(year_month)
        spent = 0.0
        for exp in expenses:
            if exp['id'] == category_id:
                spent = float(exp['total']) if exp.get('total') else 0.0
                break
        ratio = spent / budget if budget > 0 else 0
        return {
            'budget': budget,
            'spent': spent,
            'remaining': budget - spent,
            'ratio': ratio,
            'status': self._calc_status(ratio, budget > 0)
        }

    def get_category_budget_status_tree(self, year_month):
        expense_data = self._tx_repo.get_category_expense_summary(year_month)
        category_budgets = self._budget_repo.get_all(year_month)
        expense_categories = self._cat_repo.get_all('expense', parent_only=True)
        all_subcategories = {}
        for parent in expense_categories:
            all_subcategories[parent['id']] = self._cat_repo.get_subcategories(parent['id'])

        budget_map = {}
        for b in category_budgets:
            if b.get('category_id'):
                budget_map[b['category_id']] = b

        expense_map = {}
        for exp in expense_data:
            expense_map[exp['id']] = float(exp['total']) if exp.get('total') else 0.0

        result = []
        for parent in expense_categories:
            pid = parent['id']
            parent_budget = budget_map.get(pid)
            parent_budget_amount = float(parent_budget['amount']) if parent_budget and parent_budget.get('amount') else 0.0
            if parent_budget_amount < 0:
                parent_budget_amount = 0.0
            parent_direct_spent = float(expense_map.get(pid, 0.0))
            if parent_direct_spent < 0:
                parent_direct_spent = 0.0

            children_status = []
            children_total_spent = 0.0
            for sub in all_subcategories.get(pid, []):
                sid = sub['id']
                sub_budget = budget_map.get(sid)
                sub_budget_amount = float(sub_budget['amount']) if sub_budget and sub_budget.get('amount') else 0.0
                if sub_budget_amount < 0:
                    sub_budget_amount = 0.0
                sub_spent = float(expense_map.get(sid, 0.0))
                if sub_spent < 0:
                    sub_spent = 0.0
                children_total_spent += sub_spent

                sub_ratio = sub_spent / sub_budget_amount if sub_budget_amount > 0 else 0
                sub_status = self._calc_status(sub_ratio, sub_budget_amount > 0)

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
            status = self._calc_status(ratio, parent_budget_amount > 0)

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
        if total_status['status'] in ('warning', 'danger') and total_status['budget'] > 0:
            pct = total_status['ratio'] * 100
            msg = f'总预算已使用 {pct:.1f}%，剩余 ¥{total_status["remaining"]:.2f}'
            warnings.append({'type': total_status['status'], 'message': msg})

        tree = self.get_category_budget_status_tree(year_month)
        for parent in tree:
            if parent['status'] in ('warning', 'danger') and parent['budget'] > 0:
                pct = parent['ratio'] * 100
                msg = f'{parent["category_icon"]} {parent["category_name"]}预算已使用 {pct:.1f}%'
                warnings.append({'type': parent['status'], 'message': msg})
            for child in parent.get('children', []):
                if child['status'] in ('warning', 'danger') and child['budget'] > 0:
                    pct = child['ratio'] * 100
                    msg = f'{parent["category_icon"]} {parent["category_name"]} > {child["category_icon"]} {child["category_name"]}预算已使用 {pct:.1f}%'
                    warnings.append({'type': child['status'], 'message': msg})

        return warnings


class _DSCompatAdapter:
    def __init__(self, tx_repo, budget_repo, cat_repo):
        self._tx = tx_repo
        self._budget = budget_repo
        self._cat = cat_repo

    def get_monthly_summary(self, ym):
        return self._tx.get_monthly_summary(ym)

    def get_category_expense_summary(self, ym):
        return self._tx.get_category_expense_summary(ym)

    def get_categories(self, type_=None, parent_only=False):
        return self._cat.get_all(type_=type_, parent_only=parent_only)

    def get_subcategories(self, parent_id):
        return self._cat.get_subcategories(parent_id)

    def get_budgets(self, ym):
        return self._budget.get_all(ym)

    def normalize_date(self, v):
        return DatabaseConnection.normalize_date(v)

    def normalize_year_month(self, v):
        return DatabaseConnection.normalize_year_month(v)
