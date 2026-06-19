from database import DatabaseConnection
from repositories import TransactionRepository, CategoryRepository, AccountRepository
from reports import (
    MonthlyTrendChart, CategoryPieChart, AccountBalanceChart,
    SummaryTable, ExportService
)


class ReportGenerator:
    def __init__(self, ledger_or_ds=None, db=None):
        if ledger_or_ds is not None and hasattr(ledger_or_ds, '_tx_repo'):
            ledger = ledger_or_ds
            self.tx_repo = ledger._tx_repo
            self.cat_repo = ledger._cat_repo
            self.acc_repo = ledger._acc_repo
        elif ledger_or_ds is not None and hasattr(ledger_or_ds, '_tx'):
            ds = ledger_or_ds
            self.tx_repo = ds._tx
            self.cat_repo = ds._cat
            self.acc_repo = ds._acc
        else:
            if db is None:
                db = DatabaseConnection()
            self.tx_repo = TransactionRepository(db)
            self.cat_repo = CategoryRepository(db)
            self.acc_repo = AccountRepository(db)
        self.ds = _CompatAdapter(self.tx_repo, self.cat_repo, self.acc_repo)
        self.summary_table = SummaryTable(self.tx_repo, self.cat_repo)
        self.export_service = ExportService(self.tx_repo, self.cat_repo, self.acc_repo)

    # ==================== Charts ====================

    def create_monthly_trend_chart(self, parent, months=6, figsize=(6, 4)):
        chart = MonthlyTrendChart(self.tx_repo, parent=parent, figsize=figsize)
        return chart.render(months=months)

    def create_expense_pie_chart(self, parent, year_month, figsize=(5, 4)):
        chart = CategoryPieChart(self.tx_repo, self.cat_repo, parent=parent, figsize=figsize)
        return chart.render(year_month, type_='expense')

    def create_income_pie_chart(self, parent, year_month, figsize=(5, 4)):
        chart = CategoryPieChart(self.tx_repo, self.cat_repo, parent=parent, figsize=figsize)
        return chart.render(year_month, type_='income')

    def create_account_balance_chart(self, parent, figsize=(6, 4)):
        chart = AccountBalanceChart(self.acc_repo, parent=parent, figsize=figsize)
        return chart.render()

    # ==================== Summary Data ====================

    def create_category_summary_table_data(self, year_month):
        return self.summary_table.build(year_month)

    # ==================== CSV Export ====================

    def export_monthly_csv(self, year_month, output_path):
        return self.export_service.export_monthly_csv(year_month, output_path)

    def export_category_summary_csv(self, year_month, output_path):
        return self.export_service.export_category_summary_csv(year_month, output_path)


class _CompatAdapter:
    def __init__(self, tx_repo, cat_repo, acc_repo):
        self._tx = tx_repo
        self._cat = cat_repo
        self._acc = acc_repo

    def get_monthly_summary(self, ym):
        return self._tx.get_monthly_summary(ym)

    def get_category_expense_summary(self, ym):
        return self._tx.get_category_expense_summary(ym)

    def get_category_expense_summary_with_parent(self, ym):
        return self._tx.get_category_expense_summary_with_parent(ym)

    def get_category_income_summary(self, ym):
        return self._tx.get_category_income_summary(ym)

    def get_monthly_trend(self, months=6):
        return self._tx.get_monthly_trend(months)

    def get_account_balances(self):
        return self._acc.get_balances()

    def get_categories(self, type_=None, parent_only=False):
        return self._cat.get_all(type_=type_, parent_only=parent_only)

    def get_subcategories(self, parent_id):
        return self._cat.get_subcategories(parent_id)

    def normalize_date(self, v):
        return DatabaseConnection.normalize_date(v)

    def normalize_year_month(self, v):
        return DatabaseConnection.normalize_year_month(v)
