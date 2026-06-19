from datetime import datetime, date, timedelta
from database import DatabaseConnection


class BaseRepository:
    def __init__(self, db):
        self.db = db

    def _to_list(self, cursor):
        return [dict(row) for row in cursor.fetchall()]

    def _to_one(self, cursor):
        row = cursor.fetchone()
        return dict(row) if row else None


class CategoryRepository(BaseRepository):
    def get_all(self, type_=None, parent_only=False):
        cursor = self.db.cursor()
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
        return self._to_list(cursor)

    def get_subcategories(self, parent_id):
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM categories WHERE parent_id = ? ORDER BY id', (parent_id,))
        return self._to_list(cursor)

    def get_tree(self, type_=None):
        parents = self.get_all(type_=type_, parent_only=True)
        result = []
        for p in parents:
            node = dict(p)
            node['children'] = self.get_subcategories(p['id'])
            result.append(node)
        return result


class AccountRepository(BaseRepository):
    def get_all(self):
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM accounts ORDER BY id')
        return self._to_list(cursor)

    def get(self, account_id):
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM accounts WHERE id=?', (account_id,))
        return self._to_one(cursor)

    def add(self, name, type_='cash', balance=0):
        cursor = self.db.cursor()
        cursor.execute(
            'INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)',
            (name, type_, balance)
        )
        self.db.commit()
        return cursor.lastrowid

    def update(self, account_id, name=None, type_=None, balance=None):
        cursor = self.db.cursor()
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
        self.db.commit()
        return cursor.rowcount > 0

    def delete(self, account_id):
        cursor = self.db.cursor()
        cursor.execute(
            'SELECT COUNT(*) as c FROM transactions WHERE account_id=? OR to_account_id=?',
            (account_id, account_id)
        )
        if cursor.fetchone()['c'] > 0:
            return False
        cursor.execute('DELETE FROM accounts WHERE id=?', (account_id,))
        self.db.commit()
        return cursor.rowcount > 0

    def get_balances(self):
        accounts = self.get_all()
        cursor = self.db.cursor()
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

    def get_balance(self, account_id):
        for a in self.get_balances():
            if a['id'] == account_id:
                return a['current_balance']
        return 0


class TransactionRepository(BaseRepository):
    def add(self, date_str, amount, type_, category_id, account_id,
            note='', to_account_id=None, recurring_rule_id=None):
        date_str = DatabaseConnection.normalize_date(date_str)
        cursor = self.db.cursor()
        cursor.execute(
            '''INSERT INTO transactions 
               (date, amount, type, category_id, account_id, to_account_id, note, recurring_rule_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (date_str, amount, type_, category_id, account_id, to_account_id, note, recurring_rule_id)
        )
        self.db.commit()
        return cursor.lastrowid

    def add_transfer(self, date_str, amount, from_account_id, to_account_id, note=''):
        date_str = DatabaseConnection.normalize_date(date_str)
        cursor = self.db.cursor()
        cursor.execute(
            '''INSERT INTO transactions
               (date, amount, type, category_id, account_id, to_account_id, note)
               VALUES (?, ?, 'transfer', NULL, ?, ?, ?)''',
            (date_str, amount, from_account_id, to_account_id, note)
        )
        self.db.commit()
        return cursor.lastrowid

    def update(self, txn_id, date_str, amount, type_, category_id, account_id,
               note='', to_account_id=None):
        date_str = DatabaseConnection.normalize_date(date_str)
        cursor = self.db.cursor()
        cursor.execute(
            '''UPDATE transactions 
               SET date=?, amount=?, type=?, category_id=?, account_id=?, to_account_id=?, note=? 
               WHERE id=?''',
            (date_str, amount, type_, category_id, account_id, to_account_id, note, txn_id)
        )
        self.db.commit()
        return cursor.rowcount > 0

    def delete(self, txn_id):
        cursor = self.db.cursor()
        cursor.execute('DELETE FROM transactions WHERE id=?', (txn_id,))
        self.db.commit()
        return cursor.rowcount > 0

    def get(self, txn_id):
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT t.*, c.name as category_name, c.icon as category_icon,
                   a.name as account_name, ta.name as to_account_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            JOIN accounts a ON t.account_id = a.id
            LEFT JOIN accounts ta ON t.to_account_id = ta.id
            WHERE t.id = ?
        ''', (txn_id,))
        return self._to_one(cursor)

    def find(self, start_date=None, end_date=None, type_=None,
             category_id=None, account_id=None, keyword=None,
             limit=None, offset=None, order_by='date DESC'):
        start_date = DatabaseConnection.normalize_date(start_date) if start_date else None
        end_date = DatabaseConnection.normalize_date(end_date) if end_date else None
        cursor = self.db.cursor()
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
        return self._to_list(cursor)

    def get_monthly_summary(self, year_month):
        year_month = DatabaseConnection.normalize_year_month(year_month)
        cursor = self.db.cursor()
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
        year_month = DatabaseConnection.normalize_year_month(year_month)
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT c.id, c.name, c.icon, c.parent_id,
                   SUM(t.amount) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.type = 'expense' AND strftime('%Y-%m', t.date) = ?
            GROUP BY c.id, c.name, c.icon, c.parent_id
            ORDER BY total DESC
        ''', (year_month,))
        return self._to_list(cursor)

    def get_category_expense_summary_with_parent(self, year_month):
        year_month = DatabaseConnection.normalize_year_month(year_month)
        cursor = self.db.cursor()
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
        return self._to_list(cursor)

    def get_category_income_summary(self, year_month):
        year_month = DatabaseConnection.normalize_year_month(year_month)
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT c.id, c.name, c.icon, c.parent_id,
                   SUM(t.amount) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.type = 'income' AND strftime('%Y-%m', t.date) = ?
            GROUP BY c.id, c.name, c.icon, c.parent_id
            ORDER BY total DESC
        ''', (year_month,))
        return self._to_list(cursor)

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
        for pid in parent_ids_with_sub:
            if pid not in parent_expense:
                parent_expense[pid] = {
                    'id': pid,
                    'name': expense_data[0].get('parent_name', '') if expense_data else '',
                    'icon': expense_data[0].get('parent_icon', '') if expense_data else '',
                    'parent_id': None,
                    'total': 0
                }
        return {
            'parents': list(parent_expense.values()),
            'subs': sub_expense
        }

    def get_monthly_trend(self, months=6):
        cursor = self.db.cursor()
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
        return self._to_list(cursor)


class BudgetRepository(BaseRepository):
    def set(self, year_month, amount, category_id=None):
        year_month = DatabaseConnection.normalize_year_month(year_month)
        cursor = self.db.cursor()
        budget_type = 'category' if category_id else 'total'
        cursor.execute('''
            INSERT INTO budgets (year_month, category_id, amount, type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(year_month, category_id) 
            DO UPDATE SET amount = excluded.amount
        ''', (year_month, category_id, amount, budget_type))
        self.db.commit()
        return cursor.lastrowid

    def get_all(self, year_month):
        year_month = DatabaseConnection.normalize_year_month(year_month)
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT b.*, c.name as category_name, c.icon as category_icon, c.parent_id
            FROM budgets b
            LEFT JOIN categories c ON b.category_id = c.id
            WHERE b.year_month = ?
            ORDER BY b.type, c.parent_id IS NOT NULL, b.id
        ''', (year_month,))
        return self._to_list(cursor)

    def get(self, year_month, category_id=None):
        year_month = DatabaseConnection.normalize_year_month(year_month)
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT b.*, c.name as category_name
            FROM budgets b
            LEFT JOIN categories c ON b.category_id = c.id
            WHERE b.year_month = ? AND b.category_id IS ?
        ''', (year_month, category_id))
        return self._to_one(cursor)

    def delete(self, budget_id):
        cursor = self.db.cursor()
        cursor.execute('DELETE FROM budgets WHERE id=?', (budget_id,))
        self.db.commit()
        return cursor.rowcount > 0


class RecurringRuleRepository(BaseRepository):
    @staticmethod
    def calculate_next_date(current_date_str, frequency, interval_val):
        current_date_str = DatabaseConnection.normalize_date(current_date_str)
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

    def add(self, name, frequency, interval_val, type_, amount,
            category_id, account_id, note='', to_account_id=None,
            start_date=None, end_date=None):
        start_date = DatabaseConnection.normalize_date(start_date) if start_date else date.today().strftime('%Y-%m-%d')
        end_date = DatabaseConnection.normalize_date(end_date) if end_date else None
        cursor = self.db.cursor()
        cursor.execute(
            '''INSERT INTO recurring_rules
               (name, frequency, interval_val, type, amount, category_id, account_id,
                to_account_id, note, start_date, next_date, end_date, active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)''',
            (name, frequency, interval_val, type_, amount, category_id, account_id,
             to_account_id, note, start_date, start_date, end_date)
        )
        self.db.commit()
        return cursor.lastrowid

    def get_all(self, active_only=False):
        cursor = self.db.cursor()
        base_sql = '''
            SELECT r.*, c.name as category_name, c.icon as category_icon,
                   a.name as account_name, ta.name as to_account_name
            FROM recurring_rules r
            LEFT JOIN categories c ON r.category_id = c.id
            JOIN accounts a ON r.account_id = a.id
            LEFT JOIN accounts ta ON r.to_account_id = ta.id
        '''
        if active_only:
            cursor.execute(base_sql + ' WHERE r.active = 1 ORDER BY r.next_date')
        else:
            cursor.execute(base_sql + ' ORDER BY r.active DESC, r.next_date')
        return self._to_list(cursor)

    def get(self, rule_id):
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM recurring_rules WHERE id=?', (rule_id,))
        return self._to_one(cursor)

    def update(self, rule_id, name=None, frequency=None, interval_val=None,
               amount=None, note=None, end_date=None, active=None):
        cursor = self.db.cursor()
        fields = []
        params = []
        for col, val in [('name', name), ('frequency', frequency), ('interval_val', interval_val),
                         ('amount', amount), ('note', note),
                         ('end_date', DatabaseConnection.normalize_date(end_date) if end_date is not None else None),
                         ('active', active)]:
            if val is not None:
                fields.append(f'{col} = ?')
                params.append(val)
        if not fields:
            return False
        params.append(rule_id)
        cursor.execute(f'UPDATE recurring_rules SET {", ".join(fields)} WHERE id=?', params)
        self.db.commit()
        return cursor.rowcount > 0

    def update_next_date(self, rule_id, next_date):
        next_date = DatabaseConnection.normalize_date(next_date)
        cursor = self.db.cursor()
        cursor.execute('UPDATE recurring_rules SET next_date=? WHERE id=?', (next_date, rule_id))
        self.db.commit()

    def deactivate(self, rule_id):
        cursor = self.db.cursor()
        cursor.execute('UPDATE recurring_rules SET active=0 WHERE id=?', (rule_id,))
        self.db.commit()

    def delete(self, rule_id):
        cursor = self.db.cursor()
        cursor.execute('DELETE FROM recurring_rules WHERE id=?', (rule_id,))
        self.db.commit()
        return cursor.rowcount > 0

    def get_due(self, today_str=None):
        if today_str is None:
            today_str = date.today().strftime('%Y-%m-%d')
        today_str = DatabaseConnection.normalize_date(today_str)
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT * FROM recurring_rules
            WHERE active = 1 AND next_date <= ?
            ORDER BY next_date
        ''', (today_str,))
        return self._to_list(cursor)
