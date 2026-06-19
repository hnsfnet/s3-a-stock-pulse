from database import DatabaseConnection, SchemaMigrator
from repositories import (
    TransactionRepository, CategoryRepository, AccountRepository,
    BudgetRepository, RecurringRuleRepository
)


class DataStore:
    normalize_date = staticmethod(DatabaseConnection.normalize_date)
    normalize_year_month = staticmethod(DatabaseConnection.normalize_year_month)
    calculate_next_date = staticmethod(RecurringRuleRepository.calculate_next_date)

    def __init__(self, db_path=None):
        self.db = DatabaseConnection(db_path)
        SchemaMigrator(self.db).initialize()
        self.conn = self.db.conn
        self._tx = TransactionRepository(self.db)
        self._cat = CategoryRepository(self.db)
        self._acc = AccountRepository(self.db)
        self._budget = BudgetRepository(self.db)
        self._rr = RecurringRuleRepository(self.db)

    def close(self):
        self.db.close()

    # ==================== Transaction CRUD ====================

    def add_transaction(self, *args, **kwargs):
        return self._tx.add(*args, **kwargs)

    def add_transfer(self, *args, **kwargs):
        return self._tx.add_transfer(*args, **kwargs)

    def update_transaction(self, *args, **kwargs):
        return self._tx.update(*args, **kwargs)

    def delete_transaction(self, txn_id):
        return self._tx.delete(txn_id)

    def get_transaction(self, txn_id):
        return self._tx.get(txn_id)

    def get_transactions(self, *args, **kwargs):
        return self._tx.find(*args, **kwargs)

    # ==================== Category ====================

    def get_categories(self, *args, **kwargs):
        return self._cat.get_all(*args, **kwargs)

    def get_subcategories(self, parent_id):
        return self._cat.get_subcategories(parent_id)

    def get_category_tree(self, *args, **kwargs):
        return self._cat.get_tree(*args, **kwargs)

    # ==================== Account ====================

    def get_accounts(self):
        return self._acc.get_all()

    def get_account(self, account_id):
        return self._acc.get(account_id)

    def add_account(self, *args, **kwargs):
        return self._acc.add(*args, **kwargs)

    def update_account(self, *args, **kwargs):
        return self._acc.update(*args, **kwargs)

    def delete_account(self, account_id):
        return self._acc.delete(account_id)

    def get_account_balances(self):
        return self._acc.get_balances()

    def get_account_balance(self, account_id):
        return self._acc.get_balance(account_id)

    # ==================== Summary / Reports ====================

    def get_monthly_summary(self, *args, **kwargs):
        return self._tx.get_monthly_summary(*args, **kwargs)

    def get_category_expense_summary(self, *args, **kwargs):
        return self._tx.get_category_expense_summary(*args, **kwargs)

    def get_category_expense_summary_with_parent(self, *args, **kwargs):
        return self._tx.get_category_expense_summary_with_parent(*args, **kwargs)

    def get_category_income_summary(self, *args, **kwargs):
        return self._tx.get_category_income_summary(*args, **kwargs)

    def get_expense_by_category_tree(self, *args, **kwargs):
        return self._tx.get_expense_by_category_tree(*args, **kwargs)

    def get_monthly_trend(self, *args, **kwargs):
        return self._tx.get_monthly_trend(*args, **kwargs)

    # ==================== Budget ====================

    def set_budget(self, *args, **kwargs):
        return self._budget.set(*args, **kwargs)

    def get_budgets(self, *args, **kwargs):
        return self._budget.get_all(*args, **kwargs)

    def get_budget(self, *args, **kwargs):
        return self._budget.get(*args, **kwargs)

    def delete_budget(self, budget_id):
        return self._budget.delete(budget_id)

    # ==================== Recurring Rules ====================

    def add_recurring_rule(self, *args, **kwargs):
        return self._rr.add(*args, **kwargs)

    def get_recurring_rules(self, *args, **kwargs):
        return self._rr.get_all(*args, **kwargs)

    def get_recurring_rule(self, rule_id):
        return self._rr.get(rule_id)

    def update_recurring_rule(self, *args, **kwargs):
        return self._rr.update(*args, **kwargs)

    def update_recurring_next_date(self, *args, **kwargs):
        return self._rr.update_next_date(*args, **kwargs)

    def deactivate_recurring_rule(self, rule_id):
        return self._rr.deactivate(rule_id)

    def delete_recurring_rule(self, rule_id):
        return self._rr.delete(rule_id)

    def get_due_recurring_rules(self, *args, **kwargs):
        return self._rr.get_due(*args, **kwargs)
