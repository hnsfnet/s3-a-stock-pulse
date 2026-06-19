from datastore import DataStore
from datetime import datetime


class Ledger:
    def __init__(self, datastore: DataStore):
        self.ds = datastore

    def add_income(self, date, amount, category_id, account_id, note=''):
        if amount <= 0:
            raise ValueError('金额必须大于0')
        return self.ds.add_transaction(date, amount, 'income', category_id, account_id, note)

    def add_expense(self, date, amount, category_id, account_id, note=''):
        if amount <= 0:
            raise ValueError('金额必须大于0')
        return self.ds.add_transaction(date, amount, 'expense', category_id, account_id, note)

    def add_transaction(self, date, amount, type_, category_id, account_id, note=''):
        if amount <= 0:
            raise ValueError('金额必须大于0')
        if type_ not in ('income', 'expense'):
            raise ValueError('类型必须是 income 或 expense')
        return self.ds.add_transaction(date, amount, type_, category_id, account_id, note)

    def update_transaction(self, txn_id, date, amount, type_, category_id, account_id, note=''):
        if amount <= 0:
            raise ValueError('金额必须大于0')
        return self.ds.update_transaction(txn_id, date, amount, type_, category_id, account_id, note)

    def delete_transaction(self, txn_id):
        return self.ds.delete_transaction(txn_id)

    def get_transaction(self, txn_id):
        return self.ds.get_transaction(txn_id)

    def list_transactions(self, start_date=None, end_date=None, type_=None,
                          category_id=None, keyword=None, limit=None, offset=None):
        return self.ds.get_transactions(
            start_date=start_date,
            end_date=end_date,
            type_=type_,
            category_id=category_id,
            keyword=keyword,
            limit=limit,
            offset=offset
        )

    def get_recent_transactions(self, limit=10):
        return self.ds.get_transactions(limit=limit, order_by='date DESC')

    def get_categories(self, type_=None):
        return self.ds.get_categories(type_)

    def get_accounts(self):
        return self.ds.get_accounts()

    def get_monthly_summary(self, year_month):
        return self.ds.get_monthly_summary(year_month)

    def get_category_expense_summary(self, year_month):
        return self.ds.get_category_expense_summary(year_month)

    def get_monthly_trend(self, months=6):
        return self.ds.get_monthly_trend(months)

    def get_current_month_str(self):
        return datetime.now().strftime('%Y-%m')
