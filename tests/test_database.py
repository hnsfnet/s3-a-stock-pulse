import os
import sys
import tempfile
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseConnection, SchemaMigrator
from repositories import TransactionRepository, CategoryRepository, AccountRepository


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    try:
        db = DatabaseConnection(db_path)
        SchemaMigrator(db).initialize()
        yield db
    finally:
        db.close()
        if os.path.exists(db_path):
            os.unlink(db_path)


class TestDatabaseConnection:
    def test_connection(self, temp_db):
        assert temp_db.conn is not None
        assert temp_db.db_path is not None

    def test_normalize_date(self):
        from datetime import datetime
        assert DatabaseConnection.normalize_date('2024-01-15') == '2024-01-15'
        assert DatabaseConnection.normalize_date(datetime(2024, 1, 15, 10, 30)) == '2024-01-15'
        assert DatabaseConnection.normalize_date(None) is None
        result = DatabaseConnection.normalize_date('invalid')
        assert result is not None and len(result) == 10

    def test_normalize_year_month(self):
        assert DatabaseConnection.normalize_year_month('2024-01') == '2024-01'
        assert DatabaseConnection.normalize_year_month('2024-01-15') == '2024-01'
        assert DatabaseConnection.normalize_year_month(None) is None


class TestSchemaMigrator:
    def test_initialize(self, temp_db):
        cursor = temp_db.cursor()
        cursor.execute("SELECT MAX(version) as v FROM schema_version")
        row = cursor.fetchone()
        assert row['v'] == 4

    def test_default_categories(self, temp_db):
        cat_repo = CategoryRepository(temp_db)
        cats = cat_repo.get_all()
        assert len(cats) > 0

    def test_default_accounts(self, temp_db):
        acc_repo = AccountRepository(temp_db)
        accounts = acc_repo.get_all()
        assert len(accounts) == 4


class TestTransactionRepository:
    def test_add_and_get_transaction(self, temp_db):
        tx_repo = TransactionRepository(temp_db)
        cat_repo = CategoryRepository(temp_db)
        acc_repo = AccountRepository(temp_db)

        accounts = acc_repo.get_all()
        assert len(accounts) > 0
        account_id = accounts[0]['id']

        income_cats = cat_repo.get_all(type_='income', parent_only=True)
        assert len(income_cats) > 0
        category_id = income_cats[0]['id']

        txn_id = tx_repo.add(
            date_str='2024-01-15',
            amount=100.0,
            type_='income',
            category_id=category_id,
            account_id=account_id,
            note='Test income'
        )
        assert txn_id > 0

        txn = tx_repo.get(txn_id)
        assert txn is not None
        assert txn['amount'] == 100.0
        assert txn['type'] == 'income'
        assert txn['date'] == '2024-01-15'

    def test_get_monthly_summary(self, temp_db):
        tx_repo = TransactionRepository(temp_db)
        cat_repo = CategoryRepository(temp_db)
        acc_repo = AccountRepository(temp_db)

        account_id = acc_repo.get_all()[0]['id']
        income_cat = cat_repo.get_all(type_='income', parent_only=True)[0]['id']
        expense_cat = cat_repo.get_all(type_='expense', parent_only=True)[0]['id']

        tx_repo.add('2024-01-15', 500.0, 'income', income_cat, account_id, 'Income 1')
        tx_repo.add('2024-01-20', 300.0, 'expense', expense_cat, account_id, 'Expense 1')

        summary = tx_repo.get_monthly_summary('2024-01')
        assert summary['total_income'] == 500.0
        assert summary['total_expense'] == 300.0
