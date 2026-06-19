import sqlite3
import os
from datetime import datetime, date, timedelta


class DataStore:
    @staticmethod
    def normalize_date(date_val):
        if date_val is None:
            return None
        if isinstance(date_val, datetime):
            return date_val.strftime('%Y-%m-%d')
        if isinstance(date_val, date):
            return date_val.strftime('%Y-%m-%d')
        if isinstance(date_val, str):
            s = date_val.strip()
            if len(s) >= 10 and s[4] == '-' and s[7] == '-':
                return s[:10]
            try:
                dt = datetime.strptime(s, '%Y-%m-%d')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                try:
                    dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
                    return dt.strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    return date.today().strftime('%Y-%m-%d')
        return date.today().strftime('%Y-%m-%d')

    @staticmethod
    def normalize_year_month(ym):
        if ym is None:
            return None
        if isinstance(ym, str):
            s = ym.strip()
            if len(s) >= 7 and s[4] == '-':
                return s[:7]
        return date.today().strftime('%Y-%m')

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ledger.db')
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
        self._init_tables()
        self._migrate_schema()
        self._init_default_categories()
        self._init_default_subcategories()
        self._init_default_accounts()

    def _init_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                icon TEXT,
                parent_id INTEGER,
                FOREIGN KEY (parent_id) REFERENCES categories(id)
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
                type TEXT NOT NULL CHECK(type IN ('income', 'expense', 'transfer')),
                category_id INTEGER,
                account_id INTEGER NOT NULL,
                to_account_id INTEGER,
                note TEXT DEFAULT '',
                recurring_rule_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                FOREIGN KEY (to_account_id) REFERENCES accounts(id)
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year_month TEXT NOT NULL,
                category_id INTEGER,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('total', 'category')),
                UNIQUE(year_month, category_id)
            );

            CREATE TABLE IF NOT EXISTS recurring_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT '',
                frequency TEXT NOT NULL CHECK(frequency IN ('daily', 'weekly', 'monthly', 'yearly')),
                interval_val INTEGER NOT NULL DEFAULT 1,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense', 'transfer')),
                amount REAL NOT NULL,
                category_id INTEGER,
                account_id INTEGER NOT NULL,
                to_account_id INTEGER,
                note TEXT DEFAULT '',
                start_date TEXT NOT NULL,
                next_date TEXT NOT NULL,
                end_date TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                FOREIGN KEY (to_account_id) REFERENCES accounts(id)
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
            CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
            CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
            CREATE INDEX IF NOT EXISTS idx_budgets_ym ON budgets(year_month);
            CREATE INDEX IF NOT EXISTS idx_recurring_next ON recurring_rules(next_date);
            CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);
        ''')
        self.conn.commit()

    def _migrate_schema(self):
        cursor = self.conn.cursor()

        try:
            cursor.execute('ALTER TABLE categories ADD COLUMN parent_id INTEGER')
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE transactions ADD COLUMN to_account_id INTEGER')
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE transactions ADD COLUMN recurring_rule_id INTEGER')
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='transactions'")
        result = cursor.fetchone()
        if result and 'transfer' not in result[0]:
            cursor.executescript('''
                CREATE TABLE transactions_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('income', 'expense', 'transfer')),
                    category_id INTEGER,
                    account_id INTEGER NOT NULL,
                    to_account_id INTEGER,
                    note TEXT DEFAULT '',
                    recurring_rule_id INTEGER,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (category_id) REFERENCES categories(id),
                    FOREIGN KEY (account_id) REFERENCES accounts(id),
                    FOREIGN KEY (to_account_id) REFERENCES accounts(id)
                );
                INSERT INTO transactions_new (id, date, amount, type, category_id, account_id, note, created_at)
                SELECT id, date, amount, type, category_id, account_id, note, created_at FROM transactions;
                DROP TABLE transactions;
                ALTER TABLE transactions_new RENAME TO transactions;
                CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
                CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
                CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
            ''')
            self.conn.commit()

        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='categories'")
        result = cursor.fetchone()
        if result and 'parent_id' not in result[0]:
            try:
                cursor.execute('ALTER TABLE categories ADD COLUMN parent_id INTEGER')
                self.conn.commit()
            except sqlite3.OperationalError:
                pass

    def _init_default_categories(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM categories WHERE parent_id IS NULL')
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
                'INSERT INTO categories (name, type, icon, parent_id) VALUES (?, ?, ?, NULL)',
                default_categories
            )
            self.conn.commit()

    def _init_default_subcategories(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM categories WHERE parent_id IS NOT NULL')
        if cursor.fetchone()[0] > 0:
            return

        parent_map = {}
        cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NULL")
        for row in cursor.fetchall():
            parent_map[row['name']] = row['id']

        subcategories = [
            ('外卖', 'expense', '🍱', '餐饮'),
            ('堂食', 'expense', '🍽️', '餐饮'),
            ('买菜', 'expense', '🥬', '餐饮'),
            ('地铁', 'expense', '🚇', '交通'),
            ('打车', 'expense', '🚕', '交通'),
            ('加油', 'expense', '⛽', '交通'),
            ('服饰', 'expense', '👕', '购物'),
            ('数码', 'expense', '📱', '购物'),
            ('日用', 'expense', '🧴', '购物'),
        ]
        for name, type_, icon, parent_name in subcategories:
            parent_id = parent_map.get(parent_name)
            if parent_id:
                cursor.execute(
                    'INSERT OR IGNORE INTO categories (name, type, icon, parent_id) VALUES (?, ?, ?, ?)',
                    (name, type_, icon, parent_id)
                )
        self.conn.commit()

    def _init_default_accounts(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM accounts')
        if cursor.fetchone()[0] == 0:
            default_accounts = [
                ('现金', 'cash', 0),
                ('银行卡', 'bank', 0),
                ('信用卡', 'credit', 0),
                ('支付宝', 'alipay', 0),
            ]
            cursor.executemany(
                'INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)',
                default_accounts
            )
            self.conn.commit()

    def close(self):
        self.conn.close()

    # ==================== Transaction CRUD ====================

    def add_transaction(self, date_str, amount, type_, category_id, account_id,
                        note='', to_account_id=None, recurring_rule_id=None):
        date_str = DataStore.normalize_date(date_str)
        cursor = self.conn.cursor()
        cursor.execute(
            '''INSERT INTO transactions 
               (date, amount, type, category_id, account_id, to_account_id, note, recurring_rule_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (date_str, amount, type_, category_id, account_id, to_account_id, note, recurring_rule_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def add_transfer(self, date_str, amount, from_account_id, to_account_id, note=''):
        date_str = DataStore.normalize_date(date_str)
        cursor = self.conn.cursor()
        cursor.execute(
            '''INSERT INTO transactions
               (date, amount, type, category_id, account_id, to_account_id, note)
               VALUES (?, ?, 'transfer', NULL, ?, ?, ?)''',
            (date_str, amount, from_account_id, to_account_id, note)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_transaction(self, txn_id, date_str, amount, type_, category_id, account_id,
                           note='', to_account_id=None):
        date_str = DataStore.normalize_date(date_str)
        cursor = self.conn.cursor()
        cursor.execute(
            '''UPDATE transactions 
               SET date=?, amount=?, type=?, category_id=?, account_id=?, to_account_id=?, note=? 
               WHERE id=?''',
            (date_str, amount, type_, category_id, account_id, to_account_id, note, txn_id)
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
            SELECT t.*, c.name as category_name, c.icon as category_icon,
                   a.name as account_name, ta.name as to_account_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            JOIN accounts a ON t.account_id = a.id
            LEFT JOIN accounts ta ON t.to_account_id = ta.id
            WHERE t.id = ?
        ''', (txn_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_transactions(self, start_date=None, end_date=None, type_=None,
                         category_id=None, account_id=None, keyword=None,
                         limit=None, offset=None, order_by='date DESC'):
        start_date = DataStore.normalize_date(start_date) if start_date else None
        end_date = DataStore.normalize_date(end_date) if end_date else None
        cursor = self.conn.cursor()
        query = '''
            SELECT t.*, c.name as category_name, c.icon as category_icon,
                   a.name as account_name, ta.name as to_account_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            JOIN accounts a ON t.account_id = a.id
            LEFT JOIN accounts ta ON t.to_account_id = ta.id
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
        if account_id:
            query += ' AND (t.account_id = ? OR t.to_account_id = ?)'
            params.extend([account_id, account_id])
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

    # ==================== Category ====================

    def get_categories(self, type_=None, parent_only=False):
        cursor = self.conn.cursor()
        query = 'SELECT * FROM categories'
        conditions = []
        params = []
        if type_:
            conditions.append('type = ?')
            params.append(type_)
        if parent_only:
            conditions.append('parent_id IS NULL')
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        query += ' ORDER BY parent_id IS NOT NULL, parent_id, id'
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_subcategories(self, parent_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE parent_id = ? ORDER BY id', (parent_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_category_tree(self, type_=None):
        parents = self.get_categories(type_=type_, parent_only=True)
        tree = []
        for p in parents:
            node = dict(p)
            node['children'] = self.get_subcategories(p['id'])
            tree.append(node)
        return tree

    # ==================== Account CRUD ====================

    def get_accounts(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM accounts ORDER BY id')
        return [dict(row) for row in cursor.fetchall()]

    def get_account(self, account_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM accounts WHERE id=?', (account_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def add_account(self, name, type_='cash', balance=0):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)',
            (name, type_, balance)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_account(self, account_id, name=None, type_=None, balance=None):
        cursor = self.conn.cursor()
        fields = []
        params = []
        if name is not None:
            fields.append('name = ?')
            params.append(name)
        if type_ is not None:
            fields.append('type = ?')
            params.append(type_)
        if balance is not None:
            fields.append('balance = ?')
            params.append(balance)
        if not fields:
            return False
        params.append(account_id)
        cursor.execute(f'UPDATE accounts SET {", ".join(fields)} WHERE id=?', params)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_account(self, account_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM transactions WHERE account_id=? OR to_account_id=?',
                       (account_id, account_id))
        if cursor.fetchone()[0] > 0:
            return False
        cursor.execute('DELETE FROM accounts WHERE id=?', (account_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_account_balances(self):
        accounts = self.get_accounts()
        cursor = self.conn.cursor()
        result = []
        for acc in accounts:
            acc_id = acc['id']
            initial = acc['balance'] or 0

            cursor.execute(
                'SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE account_id=? AND type="income"',
                (acc_id,)
            )
            income_in = cursor.fetchone()['total']

            cursor.execute(
                'SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE account_id=? AND type="expense"',
                (acc_id,)
            )
            expense_out = cursor.fetchone()['total']

            cursor.execute(
                'SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE to_account_id=? AND type="transfer"',
                (acc_id,)
            )
            transfer_in = cursor.fetchone()['total']

            cursor.execute(
                'SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE account_id=? AND type="transfer"',
                (acc_id,)
            )
            transfer_out = cursor.fetchone()['total']

            current = initial + income_in - expense_out + transfer_in - transfer_out
            result.append({
                'id': acc_id,
                'name': acc['name'],
                'type': acc['type'],
                'initial_balance': initial,
                'current_balance': current
            })
        return result

    def get_account_balance(self, account_id):
        accounts = self.get_account_balances()
        for a in accounts:
            if a['id'] == account_id:
                return a['current_balance']
        return 0

    # ==================== Summary / Reports ====================

    def get_monthly_summary(self, year_month):
        year_month = DataStore.normalize_year_month(year_month)
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as total_expense
            FROM transactions
            WHERE type IN ('income', 'expense') AND strftime('%Y-%m', date) = ?
        ''', (year_month,))
        row = cursor.fetchone()
        return {
            'total_income': row['total_income'],
            'total_expense': row['total_expense'],
            'balance': row['total_income'] - row['total_expense']
        }

    def get_category_expense_summary(self, year_month):
        year_month = DataStore.normalize_year_month(year_month)
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.id, c.name, c.icon, c.parent_id,
                   SUM(t.amount) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.type = 'expense' AND strftime('%Y-%m', t.date) = ?
            GROUP BY c.id, c.name, c.icon, c.parent_id
            ORDER BY total DESC
        ''', (year_month,))
        return [dict(row) for row in cursor.fetchall()]

    def get_category_expense_summary_with_parent(self, year_month):
        year_month = DataStore.normalize_year_month(year_month)
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.id, c.name, c.icon, c.parent_id,
                   p.name as parent_name, p.icon as parent_icon,
                   SUM(t.amount) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            LEFT JOIN categories p ON c.parent_id = p.id
            WHERE t.type = 'expense' AND strftime('%Y-%m', t.date) = ?
            GROUP BY c.id, c.name, c.icon, c.parent_id, p.name, p.icon
            ORDER BY p.name, total DESC
        ''', (year_month,))
        return [dict(row) for row in cursor.fetchall()]

    def get_category_income_summary(self, year_month):
        year_month = DataStore.normalize_year_month(year_month)
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.id, c.name, c.icon, c.parent_id,
                   SUM(t.amount) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.type = 'income' AND strftime('%Y-%m', t.date) = ?
            GROUP BY c.id, c.name, c.icon, c.parent_id
            ORDER BY total DESC
        ''', (year_month,))
        return [dict(row) for row in cursor.fetchall()]

    def get_expense_by_category_tree(self, year_month):
        expense_data = self.get_category_expense_summary_with_parent(year_month)
        parent_expense = {}
        sub_expense = {}
        for item in expense_data:
            if item['parent_id'] is None:
                parent_expense[item['id']] = item
            else:
                if item['parent_id'] not in sub_expense:
                    sub_expense[item['parent_id']] = []
                sub_expense[item['parent_id']].append(item)

        parent_ids_with_sub = set(sub_expense.keys())
        for pid, p_exp in parent_expense.items():
            if pid in parent_ids_with_sub:
                continue
        for pid in parent_ids_with_sub:
            if pid not in parent_expense:
                parent_expense[pid] = {
                    'id': pid,
                    'name': expense_data[0].get('parent_name', ''),
                    'icon': expense_data[0].get('parent_icon', ''),
                    'parent_id': None,
                    'total': 0
                }

        return {
            'parents': list(parent_expense.values()),
            'subs': sub_expense
        }

    # ==================== Budget ====================

    def set_budget(self, year_month, amount, category_id=None):
        year_month = DataStore.normalize_year_month(year_month)
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
        year_month = DataStore.normalize_year_month(year_month)
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT b.*, c.name as category_name, c.icon as category_icon, c.parent_id
            FROM budgets b
            LEFT JOIN categories c ON b.category_id = c.id
            WHERE b.year_month = ?
            ORDER BY b.type, c.parent_id IS NOT NULL, b.id
        ''', (year_month,))
        return [dict(row) for row in cursor.fetchall()]

    def get_budget(self, year_month, category_id=None):
        year_month = DataStore.normalize_year_month(year_month)
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

    # ==================== Trend ====================

    def get_monthly_trend(self, months=6):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT
                strftime('%Y-%m', date) as month,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as expense
            FROM transactions
            WHERE type IN ('income', 'expense')
              AND date >= date('now', 'start of month', '-' || ? || ' months')
            GROUP BY month
            ORDER BY month
        ''', (months - 1,))
        return [dict(row) for row in cursor.fetchall()]

    # ==================== Recurring Rules ====================

    def add_recurring_rule(self, name, frequency, interval_val, type_, amount,
                           category_id, account_id, note='', to_account_id=None,
                           start_date=None, end_date=None):
        start_date = DataStore.normalize_date(start_date) if start_date else date.today().strftime('%Y-%m-%d')
        end_date = DataStore.normalize_date(end_date) if end_date else None
        cursor = self.conn.cursor()
        cursor.execute(
            '''INSERT INTO recurring_rules
               (name, frequency, interval_val, type, amount, category_id, account_id,
                to_account_id, note, start_date, next_date, end_date, active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)''',
            (name, frequency, interval_val, type_, amount, category_id, account_id,
             to_account_id, note, start_date, start_date, end_date)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_recurring_rules(self, active_only=False):
        cursor = self.conn.cursor()
        if active_only:
            cursor.execute('''
                SELECT r.*, c.name as category_name, c.icon as category_icon,
                       a.name as account_name, ta.name as to_account_name
                FROM recurring_rules r
                LEFT JOIN categories c ON r.category_id = c.id
                JOIN accounts a ON r.account_id = a.id
                LEFT JOIN accounts ta ON r.to_account_id = ta.id
                WHERE r.active = 1
                ORDER BY r.next_date
            ''')
        else:
            cursor.execute('''
                SELECT r.*, c.name as category_name, c.icon as category_icon,
                       a.name as account_name, ta.name as to_account_name
                FROM recurring_rules r
                LEFT JOIN categories c ON r.category_id = c.id
                JOIN accounts a ON r.account_id = a.id
                LEFT JOIN accounts ta ON r.to_account_id = ta.id
                ORDER BY r.active DESC, r.next_date
            ''')
        return [dict(row) for row in cursor.fetchall()]

    def get_recurring_rule(self, rule_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM recurring_rules WHERE id=?', (rule_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_recurring_rule(self, rule_id, name=None, frequency=None, interval_val=None,
                              amount=None, note=None, end_date=None, active=None):
        cursor = self.conn.cursor()
        fields = []
        params = []
        for col, val in [('name', name), ('frequency', frequency), ('interval_val', interval_val),
                         ('amount', amount), ('note', note),
                         ('end_date', DataStore.normalize_date(end_date) if end_date is not None else None),
                         ('active', active)]:
            if val is not None:
                fields.append(f'{col} = ?')
                params.append(val)
        if not fields:
            return False
        params.append(rule_id)
        cursor.execute(f'UPDATE recurring_rules SET {", ".join(fields)} WHERE id=?', params)
        self.conn.commit()
        return cursor.rowcount > 0

    def update_recurring_next_date(self, rule_id, next_date):
        next_date = DataStore.normalize_date(next_date)
        cursor = self.conn.cursor()
        cursor.execute('UPDATE recurring_rules SET next_date=? WHERE id=?', (next_date, rule_id))
        self.conn.commit()

    def deactivate_recurring_rule(self, rule_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE recurring_rules SET active=0 WHERE id=?', (rule_id,))
        self.conn.commit()

    def delete_recurring_rule(self, rule_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM recurring_rules WHERE id=?', (rule_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_due_recurring_rules(self, today_str=None):
        if today_str is None:
            today_str = date.today().strftime('%Y-%m-%d')
        today_str = DataStore.normalize_date(today_str)
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM recurring_rules
            WHERE active = 1 AND next_date <= ?
            ORDER BY next_date
        ''', (today_str,))
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def calculate_next_date(current_date_str, frequency, interval_val):
        current_date_str = DataStore.normalize_date(current_date_str)
        current = datetime.strptime(current_date_str, '%Y-%m-%d').date()
        if frequency == 'daily':
            return current + timedelta(days=interval_val)
        elif frequency == 'weekly':
            return current + timedelta(weeks=interval_val)
        elif frequency == 'monthly':
            month = current.month - 1 + interval_val
            year = current.year + month // 12
            month = month % 12 + 1
            day = min(current.day, 28)
            return date(year, month, day)
        elif frequency == 'yearly':
            try:
                return date(current.year + interval_val, current.month, current.day)
            except ValueError:
                return date(current.year + interval_val, current.month, 28)
        return current
