import sqlite3
import os
from datetime import datetime, date

from logger import get_logger, log_sql

logger = get_logger('database')


class DatabaseConnection:
    def __init__(self, db_path=None):
        if db_path is None:
            from config import config
            db_path = str(config.get_db_path())
        self.db_path = db_path
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Connecting to database: {self.db_path}")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')

    def cursor(self):
        return self.conn.cursor()

    def commit(self):
        log_sql(logger, "COMMIT")
        self.conn.commit()

    def rollback(self):
        log_sql(logger, "ROLLBACK")
        self.conn.rollback()

    def close(self):
        logger.info(f"Closing database connection: {self.db_path}")
        self.conn.close()

    def executescript(self, script):
        log_sql(logger, script)
        self.conn.executescript(script)
        self.conn.commit()

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


class SchemaMigrator:
    CURRENT_VERSION = 4

    def __init__(self, db):
        self.db = db
        self.logger = get_logger('migrator')

    def initialize(self):
        self.logger.info("Starting schema initialization")
        self._ensure_version_table()
        self._init_base_tables()
        current = self._get_version()
        self.logger.info(f"Current schema version: {current}, target: {self.CURRENT_VERSION}")
        if current < self.CURRENT_VERSION:
            self.logger.info(f"Migrating from version {current} to {self.CURRENT_VERSION}")
            self._migrate_from(current)
            self._set_version(self.CURRENT_VERSION)
            self.logger.info("Schema migration completed successfully")
        else:
            self.logger.info("Schema is up to date")
        self._init_default_categories()
        self._init_default_subcategories()
        self._init_default_accounts()

    def _ensure_version_table(self):
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY DEFAULT 0,
                applied_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        ''')
        cursor = self.db.cursor()
        cursor.execute('SELECT COUNT(*) FROM schema_version')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO schema_version (version) VALUES (0)')
            self.db.commit()

    def _get_version(self):
        cursor = self.db.cursor()
        cursor.execute('SELECT MAX(version) as v FROM schema_version')
        row = cursor.fetchone()
        return row['v'] if row and row['v'] is not None else 0

    def _set_version(self, version):
        cursor = self.db.cursor()
        cursor.execute('INSERT INTO schema_version (version) VALUES (?)', (version,))
        self.db.commit()

    def _init_base_tables(self):
        self.db.executescript('''
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

    def _migrate_from(self, from_version):
        cursor = self.db.cursor()
        if from_version < 1:
            self.logger.info("Migrating to version 1: adding parent_id to categories")
            try:
                cursor.execute('ALTER TABLE categories ADD COLUMN parent_id INTEGER')
                self.db.commit()
                self.logger.info("Version 1 migration completed")
            except sqlite3.OperationalError as e:
                self.logger.warning(f"Version 1 migration skipped (column may exist): {e}")
        if from_version < 2:
            self.logger.info("Migrating to version 2: adding to_account_id to transactions")
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN to_account_id INTEGER')
                self.db.commit()
                self.logger.info("Version 2 migration completed")
            except sqlite3.OperationalError as e:
                self.logger.warning(f"Version 2 migration skipped (column may exist): {e}")
        if from_version < 3:
            self.logger.info("Migrating to version 3: adding recurring_rule_id to transactions")
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN recurring_rule_id INTEGER')
                self.db.commit()
                self.logger.info("Version 3 migration completed")
            except sqlite3.OperationalError as e:
                self.logger.warning(f"Version 3 migration skipped (column may exist): {e}")
        if from_version < 4:
            self.logger.info("Migrating to version 4: adding 'transfer' type to transactions")
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='transactions'")
            result = cursor.fetchone()
            if result and 'transfer' not in (result[0] or ''):
                self.db.executescript('''
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
                    INSERT INTO transactions_new (id, date, amount, type, category_id, account_id, note, created_at, to_account_id, recurring_rule_id)
                    SELECT id, date, amount, type, category_id, account_id, note, created_at, to_account_id, recurring_rule_id FROM transactions;
                    DROP TABLE transactions;
                    ALTER TABLE transactions_new RENAME TO transactions;
                    CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
                    CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
                    CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
                    CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
                ''')

    def _init_default_categories(self):
        cursor = self.db.cursor()
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
            self.db.commit()

    def _init_default_subcategories(self):
        cursor = self.db.cursor()
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
        self.db.commit()

    def _init_default_accounts(self):
        cursor = self.db.cursor()
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
            self.db.commit()
