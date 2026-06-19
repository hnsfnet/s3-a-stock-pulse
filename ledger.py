from datastore import DataStore
from datetime import datetime, date


class Ledger:
    def __init__(self, datastore: DataStore):
        self.ds = datastore

    # ==================== Transaction ====================

    def add_transaction(self, date_str, amount, type_, category_id, account_id,
                        note='', to_account_id=None):
        if amount <= 0:
            raise ValueError('金额必须大于0')
        if type_ not in ('income', 'expense', 'transfer'):
            raise ValueError('类型必须是 income、expense 或 transfer')
        if type_ == 'transfer':
            if not to_account_id:
                raise ValueError('转账必须指定目标账户')
            if to_account_id == account_id:
                raise ValueError('转出和转入账户不能相同')
            return self.ds.add_transfer(date_str, amount, account_id, to_account_id, note)
        return self.ds.add_transaction(date_str, amount, type_, category_id, account_id, note)

    def add_income(self, date_str, amount, category_id, account_id, note=''):
        if amount <= 0:
            raise ValueError('金额必须大于0')
        return self.ds.add_transaction(date_str, amount, 'income', category_id, account_id, note)

    def add_expense(self, date_str, amount, category_id, account_id, note=''):
        if amount <= 0:
            raise ValueError('金额必须大于0')
        return self.ds.add_transaction(date_str, amount, 'expense', category_id, account_id, note)

    def add_transfer(self, date_str, amount, from_account_id, to_account_id, note=''):
        if amount <= 0:
            raise ValueError('金额必须大于0')
        if from_account_id == to_account_id:
            raise ValueError('转出和转入账户不能相同')
        return self.ds.add_transfer(date_str, amount, from_account_id, to_account_id, note)

    def update_transaction(self, txn_id, date_str, amount, type_, category_id, account_id,
                            note='', to_account_id=None):
        if amount <= 0:
            raise ValueError('金额必须大于0')
        return self.ds.update_transaction(
            txn_id, date_str, amount, type_, category_id, account_id, note, to_account_id
        )

    def delete_transaction(self, txn_id):
        return self.ds.delete_transaction(txn_id)

    def get_transaction(self, txn_id):
        return self.ds.get_transaction(txn_id)

    def list_transactions(self, start_date=None, end_date=None, type_=None,
                          category_id=None, account_id=None, keyword=None,
                          limit=None, offset=None):
        return self.ds.get_transactions(
            start_date=start_date, end_date=end_date, type_=type_,
            category_id=category_id, account_id=account_id, keyword=keyword,
            limit=limit, offset=offset
        )

    def get_recent_transactions(self, limit=10):
        return self.ds.get_transactions(limit=limit, order_by='date DESC')

    # ==================== Category ====================

    def get_categories(self, type_=None, parent_only=False):
        return self.ds.get_categories(type_=type_, parent_only=parent_only)

    def get_subcategories(self, parent_id):
        return self.ds.get_subcategories(parent_id)

    def get_category_tree(self, type_=None):
        return self.ds.get_category_tree(type_=type_)

    # ==================== Account ====================

    def get_accounts(self):
        return self.ds.get_accounts()

    def get_account(self, account_id):
        return self.ds.get_account(account_id)

    def add_account(self, name, type_='cash', balance=0):
        return self.ds.add_account(name, type_, balance)

    def update_account(self, account_id, name=None, type_=None, balance=None):
        return self.ds.update_account(account_id, name, type_, balance)

    def delete_account(self, account_id):
        return self.ds.delete_account(account_id)

    def get_account_balances(self):
        return self.ds.get_account_balances()

    def get_account_balance(self, account_id):
        return self.ds.get_account_balance(account_id)

    # ==================== Summary / Reports ====================

    def get_monthly_summary(self, year_month):
        return self.ds.get_monthly_summary(year_month)

    def refresh_data(self):
        try:
            self.ds.conn.commit()
        except Exception:
            pass
        return True

    def get_category_expense_summary(self, year_month):
        return self.ds.get_category_expense_summary(year_month)

    def get_category_expense_summary_with_parent(self, year_month):
        return self.ds.get_category_expense_summary_with_parent(year_month)

    def get_expense_by_category_tree(self, year_month):
        return self.ds.get_expense_by_category_tree(year_month)

    def get_monthly_trend(self, months=6):
        return self.ds.get_monthly_trend(months)

    def get_current_month_str(self):
        return datetime.now().strftime('%Y-%m')

    # ==================== Recurring Rules ====================

    def add_recurring_rule(self, name, frequency, interval_val, type_, amount,
                           category_id, account_id, note='', to_account_id=None,
                           start_date=None, end_date=None):
        if amount <= 0:
            raise ValueError('金额必须大于0')
        if type_ == 'transfer' and not to_account_id:
            raise ValueError('转账规则必须指定目标账户')
        if type_ == 'transfer' and to_account_id == account_id:
            raise ValueError('转出和转入账户不能相同')
        return self.ds.add_recurring_rule(
            name, frequency, interval_val, type_, amount, category_id,
            account_id, note, to_account_id, start_date, end_date
        )

    def get_recurring_rules(self, active_only=False):
        return self.ds.get_recurring_rules(active_only=active_only)

    def get_recurring_rule(self, rule_id):
        return self.ds.get_recurring_rule(rule_id)

    def update_recurring_rule(self, rule_id, **kwargs):
        return self.ds.update_recurring_rule(rule_id, **kwargs)

    def delete_recurring_rule(self, rule_id):
        return self.ds.delete_recurring_rule(rule_id)

    def process_due_recurring(self):
        today_str = date.today().strftime('%Y-%m-%d')
        due_rules = self.ds.get_due_recurring_rules(today_str)
        generated = 0
        for rule in due_rules:
            if rule['type'] == 'transfer':
                self.ds.add_transfer(
                    rule['next_date'], rule['amount'],
                    rule['account_id'], rule['to_account_id'], rule['note']
                )
            else:
                self.ds.add_transaction(
                    rule['next_date'], rule['amount'], rule['type'],
                    rule['category_id'], rule['account_id'], rule['note'],
                    recurring_rule_id=rule['id']
                )

            next_date = DataStore.calculate_next_date(
                rule['next_date'], rule['frequency'], rule['interval_val']
            )

            if rule['end_date'] and next_date.strftime('%Y-%m-%d') > rule['end_date']:
                self.ds.deactivate_recurring_rule(rule['id'])
            else:
                self.ds.update_recurring_next_date(
                    rule['id'], next_date.strftime('%Y-%m-%d')
                )
            generated += 1
        return generated
