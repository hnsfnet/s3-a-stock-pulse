import sqlite3
import os
from datetime import datetime


class DataStore:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ledger.db')
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        self._init_default_categories()
        self._init_default_accounts()

    def _init_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                icon TEXT
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL DEFAULT 'cash',
                balance REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                category_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year_month TEXT NOT NULL,
                category_id INTEGER,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('total', 'category')),
                UNIQUE(year_month, category_id)
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
            CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
            CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
            CREATE INDEX IF NOT EXISTS idx_budgets_ym ON budgets(year_month);
        ''')
        self.conn.commit()

    def _init_default_categories(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM categories')
        if cursor.fetchone()[0] == 0:
            default_categories = [
                ('工资', 'income', '💰'),
                ('奖金', 'income', '🎁'),
                ('投资收益', 'income', '📈'),
                ('其他收入', 'income', '💵'),
                ('餐饮', 'expense', '🍜'),
                ('交通', 'expense', '🚗'),
                ('购物', 'expense', '🛒'),
                ('娱乐', 'expense', '🎮'),
                ('医疗', 'expense', '💊'),
                ('教育', 'expense', '📚'),
                ('住房', 'expense', '🏠'),
                ('水电煤', 'expense', '💡'),
                ('通讯', 'expense', '📱'),
                ('其他支出', 'expense', '📦'),
            ]
            cursor.executemany(
                'INSERT INTO categories (name, type, icon) VALUES (?, ?, ?)',
                default_categories
            )
            self.conn.commit()

    def _init_default_accounts(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM accounts')
        if cursor.fetchone()[0] == 0:
            default_accounts = [
                ('现金', 'cash', 0),
                ('银行卡', 'bank', 0),
                ('支付宝', 'alipay', 0),
                ('微信', 'wechat', 0),
            ]
            cursor.executemany(
                'INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)',
                default_accounts
            )
            self.conn.commit()

    def close(self):
        self.conn.close()

    def add_transaction(self, date, amount, type_, category_id, account_id, note=''):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO transactions (date, amount, type, category_id, account_id, note) VALUES (?, ?, ?, ?, ?, ?)',
            (date, amount, type_, category_id, account_id, note)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_transaction(self, txn_id, date, amount, type_, category_id, account_id, note=''):
        cursor = self.conn.cursor()
        cursor.execute(
            '''UPDATE transactions 
               SET date=?, amount=?, type=?, category_id=?, account_id=?, note=? 
               WHERE id=?''',
            (date, amount, type_, category_id, account_id, note, txn_id)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_transaction(self, txn_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM transactions WHERE id=?', (txn_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_transaction(self, txn_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT t.*, c.name as category_name, a.name as account_name
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            JOIN accounts a ON t.account_id = a.id
            WHERE t.id = ?
        ''', (txn_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_transactions(self, start_date=None, end_date=None, type_=None,
                         category_id=None, keyword=None, limit=None, offset=None,
                         order_by='date DESC'):
        cursor = self.conn.cursor()
        query = '''
            SELECT t.*, c.name as category_name, c.icon as category_icon, a.name as account_name
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            JOIN accounts a ON t.account_id = a.id
            WHERE 1=1
        '''
        params = []

        if start_date:
            query += ' AND t.date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND t.date <= ?'
            params.append(end_date)
        if type_:
            query += ' AND t.type = ?'
            params.append(type_)
        if category_id:
            query += ' AND t.category_id = ?'
            params.append(category_id)
        if keyword:
            query += ' AND t.note LIKE ?'
            params.append(f'%{keyword}%')

        query += f' ORDER BY t.{order_by}, t.id DESC'

        if limit:
            query += ' LIMIT ?'
            params.append(limit)
            if offset:
                query += ' OFFSET ?'
                params.append(offset)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_categories(self, type_=None):
        cursor = self.conn.cursor()
        if type_:
            cursor.execute('SELECT * FROM categories WHERE type = ? ORDER BY id', (type_,))
        else:
            cursor.execute('SELECT * FROM categories ORDER BY type, id')
        return [dict(row) for row in cursor.fetchall()]

    def get_accounts(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM accounts ORDER BY id')
        return [dict(row) for row in cursor.fetchall()]

    def get_monthly_summary(self, year_month):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as total_expense
            FROM transactions
            WHERE strftime('%Y-%m', date) = ?
        ''', (year_month,))
        row = cursor.fetchone()
        return {
            'total_income': row['total_income'],
            'total_expense': row['total_expense'],
            'balance': row['total_income'] - row['total_expense']
        }

    def get_category_expense_summary(self, year_month):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.id, c.name, c.icon, SUM(t.amount) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.type = 'expense' AND strftime('%Y-%m', t.date) = ?
            GROUP BY c.id, c.name, c.icon
            ORDER BY total DESC
        ''', (year_month,))
        return [dict(row) for row in cursor.fetchall()]

    def get_category_income_summary(self, year_month):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.id, c.name, c.icon, SUM(t.amount) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.type = 'income' AND strftime('%Y-%m', t.date) = ?
            GROUP BY c.id, c.name, c.icon
            ORDER BY total DESC
        ''', (year_month,))
        return [dict(row) for row in cursor.fetchall()]

    def set_budget(self, year_month, amount, category_id=None):
        cursor = self.conn.cursor()
        budget_type = 'category' if category_id else 'total'
        cursor.execute('''
            INSERT INTO budgets (year_month, category_id, amount, type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(year_month, category_id) 
            DO UPDATE SET amount = excluded.amount
        ''', (year_month, category_id, amount, budget_type))
        self.conn.commit()
        return cursor.lastrowid

    def get_budgets(self, year_month):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT b.*, c.name as category_name, c.icon as category_icon
            FROM budgets b
            LEFT JOIN categories c ON b.category_id = c.id
            WHERE b.year_month = ?
            ORDER BY b.type, b.id
        ''', (year_month,))
        return [dict(row) for row in cursor.fetchall()]

    def get_budget(self, year_month, category_id=None):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT b.*, c.name as category_name
            FROM budgets b
            LEFT JOIN categories c ON b.category_id = c.id
            WHERE b.year_month = ? AND b.category_id IS ?
        ''', (year_month, category_id))
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_budget(self, budget_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM budgets WHERE id=?', (budget_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_monthly_trend(self, months=6):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT
                strftime('%Y-%m', date) as month,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as expense
            FROM transactions
            WHERE date >= date('now', 'start of month', '-' || ? || ' months')
            GROUP BY month
            ORDER BY month
        ''', (months - 1,))
        return [dict(row) for row in cursor.fetchall()]
