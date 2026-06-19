from datetime import date
from database import DatabaseConnection, SchemaMigrator
from repositories import (
    TransactionRepository, CategoryRepository, AccountRepository,
    BudgetRepository, RecurringRuleRepository
)


class Ledger:
    def __init__(self, db_path_or_ds=None):
        if db_path_or_ds is None or isinstance(db_path_or_ds, (str, type(None))):
            self.db = DatabaseConnection(db_path_or_ds)
            SchemaMigrator(self.db).initialize()
            self.conn = self.db.conn
            self._tx_repo = TransactionRepository(self.db)
            self._cat_repo = CategoryRepository(self.db)
            self._acc_repo = AccountRepository(self.db)
            self._budget_repo = BudgetRepository(self.db)
            self._rr_repo = RecurringRuleRepository(self.db)
        else:
            ds = db_path_or_ds
            self.db = ds.db
            self.conn = ds.conn
            self._tx_repo = ds._tx
            self._cat_repo = ds._cat
            self._acc_repo = ds._acc
            self._budget_repo = ds._budget
            self._rr_repo = ds._rr

    def get_current_month_str(self):
        return date.today().strftime('%Y-%m')

    def close(self):
        self.db.close()

    # ==================== Transactions ====================

    def add_transaction(self, date_str, amount, type_, category_id, account_id,
                        note='', to_account_id=None, recurring_rule_id=None):
        return self._tx_repo.add(
            date_str, amount, type_, category_id, account_id, note,
            to_account_id=to_account_id, recurring_rule_id=recurring_rule_id
        )

    def add_transfer(self, date_str, amount, from_account_id, to_account_id, note=''):
        return self._tx_repo.add_transfer(date_str, amount, from_account_id, to_account_id, note)

    def update_transaction(self, txn_id, date_str, amount, type_, category_id, account_id,
                           note='', to_account_id=None):
        return self._tx_repo.update(
            txn_id, date_str, amount, type_, category_id, account_id, note, to_account_id
        )

    def delete_transaction(self, txn_id):
        return self._tx_repo.delete(txn_id)

    def get_transaction(self, txn_id):
        return self._tx_repo.get(txn_id)

    def get_transactions(self, start_date=None, end_date=None, type_=None,
                         category_id=None, account_id=None, keyword=None,
                         limit=None, offset=None, order_by='date DESC'):
        return self._tx_repo.find(
            start_date=start_date, end_date=end_date, type_=type_,
            category_id=category_id, account_id=account_id, keyword=keyword,
            limit=limit, offset=offset, order_by=order_by
        )

    def list_transactions(self, start_date=None, end_date=None, type_=None,
                          category_id=None, account_id=None, keyword=None,
                          limit=None, offset=None, order_by='date DESC'):
        return self.get_transactions(
            start_date=start_date, end_date=end_date, type_=type_,
            category_id=category_id, account_id=account_id, keyword=keyword,
            limit=limit, offset=offset, order_by=order_by
        )

    def get_recent_transactions(self, limit=10):
        return self.get_transactions(limit=limit)

    # ==================== Categories ====================

    def get_categories(self, type_=None, parent_only=False):
        return self._cat_repo.get_all(type_=type_, parent_only=parent_only)

    def get_subcategories(self, parent_id):
        return self._cat_repo.get_subcategories(parent_id)

    def get_category_tree(self, type_=None):
        return self._cat_repo.get_tree(type_=type_)

    # ==================== Accounts ====================

    def get_accounts(self):
        return self._acc_repo.get_all()

    def get_account(self, account_id):
        return self._acc_repo.get(account_id)

    def add_account(self, name, type_='cash', balance=0):
        return self._acc_repo.add(name, type_, balance)

    def update_account(self, account_id, name=None, type_=None, balance=None):
        return self._acc_repo.update(account_id, name=name, type_=type_, balance=balance)

    def delete_account(self, account_id):
        return self._acc_repo.delete(account_id)

    def get_account_balances(self):
        return self._acc_repo.get_balances()

    def get_account_balance(self, account_id):
        return self._acc_repo.get_balance(account_id)

    # ==================== Summary / Reports ====================

    def get_monthly_summary(self, year_month):
        return self._tx_repo.get_monthly_summary(year_month)

    def get_category_expense_summary(self, year_month):
        return self._tx_repo.get_category_expense_summary(year_month)

    def get_category_expense_summary_with_parent(self, year_month):
        return self._tx_repo.get_category_expense_summary_with_parent(year_month)

    def get_category_income_summary(self, year_month):
        return self._tx_repo.get_category_income_summary(year_month)

    def get_expense_by_category_tree(self, year_month):
        return self._tx_repo.get_expense_by_category_tree(year_month)

    def get_monthly_trend(self, months=6):
        return self._tx_repo.get_monthly_trend(months=months)

    # ==================== Recurring Rules ====================

    def add_recurring_rule(self, name, frequency, interval_val, type_, amount,
                           category_id, account_id, note='', to_account_id=None,
                           start_date=None, end_date=None):
        return self._rr_repo.add(
            name, frequency, interval_val, type_, amount, category_id, account_id,
            note=note, to_account_id=to_account_id, start_date=start_date, end_date=end_date
        )

    def get_recurring_rules(self, active_only=False):
        return self._rr_repo.get_all(active_only=active_only)

    def get_recurring_rule(self, rule_id):
        return self._rr_repo.get(rule_id)

    def update_recurring_rule(self, rule_id, **kwargs):
        return self._rr_repo.update(rule_id, **kwargs)

    def update_recurring_next_date(self, rule_id, next_date):
        return self._rr_repo.update_next_date(rule_id, next_date)

    def deactivate_recurring_rule(self, rule_id):
        return self._rr_repo.deactivate(rule_id)

    def delete_recurring_rule(self, rule_id):
        return self._rr_repo.delete(rule_id)

    def get_due_recurring_rules(self, today_str=None):
        return self._rr_repo.get_due(today_str)

    @staticmethod
    def calculate_next_date(current_date_str, frequency, interval_val):
        return RecurringRuleRepository.calculate_next_date(current_date_str, frequency, interval_val)

    def process_due_recurring(self):
        today_str = date.today().strftime('%Y-%m-%d')
        due_rules = self.get_due_recurring_rules(today_str)
        generated = 0
        for rule in due_rules:
            if rule['type'] == 'transfer':
                self.add_transfer(
                    rule['next_date'], rule['amount'],
                    rule['account_id'], rule['to_account_id'], rule['note']
                )
            else:
                self.add_transaction(
                    rule['next_date'], rule['amount'], rule['type'],
                    rule['category_id'], rule['account_id'], rule['note'],
                    recurring_rule_id=rule['id']
                )
            next_date = RecurringRuleRepository.calculate_next_date(
                rule['next_date'], rule['frequency'], rule['interval_val']
            )
            if rule['end_date'] and next_date.strftime('%Y-%m-%d') > rule['end_date']:
                self.deactivate_recurring_rule(rule['id'])
            else:
                self.update_recurring_next_date(
                    rule['id'], next_date.strftime('%Y-%m-%d')
                )
            generated += 1
        return generated

    def refresh_data(self):
        try:
            self.db.commit()
        except Exception:
            pass
        return True
