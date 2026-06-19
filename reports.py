import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
import os

from database import DatabaseConnection
from repositories import TransactionRepository, AccountRepository, CategoryRepository

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class _BaseChart:
    def __init__(self, parent=None, figsize=(6, 4)):
        self.parent = parent
        self.figsize = figsize
        self.fig = None
        self.canvas = None

    def _new_figure(self):
        self.fig = Figure(figsize=self.figsize, dpi=100)
        return self.fig

    def _attach_to_parent(self):
        if self.parent and self.fig:
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.parent)
            self.canvas.draw()
        return self.canvas


class MonthlyTrendChart(_BaseChart):
    def __init__(self, tx_repo, parent=None, figsize=(6, 4)):
        super().__init__(parent, figsize)
        self.tx_repo = tx_repo

    def render(self, months=6):
        trend = self.tx_repo.get_monthly_trend(months=months)
        fig = self._new_figure()
        ax = fig.add_subplot(111)
        months_labels = [t['month'] for t in trend]
        income = [t['income'] for t in trend]
        expense = [t['expense'] for t in trend]
        x = range(len(months_labels))
        ax.bar([i - 0.2 for i in x], income, width=0.4, label='收入', color='#96CEB4', alpha=0.8)
        ax.bar([i + 0.2 for i in x], expense, width=0.4, label='支出', color='#FFAAAA', alpha=0.8)
        ax.set_xticks(list(x))
        ax.set_xticklabels(months_labels, rotation=30, ha='right')
        ax.legend(loc='upper left', fontsize=8)
        ax.set_ylabel('金额 (¥)')
        ax.set_title(f'近 {months} 个月收支趋势', fontsize=10)
        ax.tick_params(axis='both', labelsize=8)
        fig.tight_layout()
        self._attach_to_parent()
        return self.canvas


class CategoryPieChart(_BaseChart):
    def __init__(self, tx_repo, cat_repo, parent=None, figsize=(5, 4)):
        super().__init__(parent, figsize)
        self.tx_repo = tx_repo
        self.cat_repo = cat_repo

    def render(self, year_month, type_='expense'):
        if type_ == 'expense':
            data = self.tx_repo.get_category_expense_summary(year_month)
        else:
            data = self.tx_repo.get_category_income_summary(year_month)

        data = [d for d in data if d.get('parent_id') is None]
        fig = self._new_figure()
        if not data:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            fig.tight_layout()
            self._attach_to_parent()
            return self.canvas

        labels = [f"{d.get('icon', '')} {d['name']}" for d in data]
        values = [d['total'] for d in data]
        colors = ['#FFB3BA', '#FFDFBA', '#FFFFBA', '#BAFFC9', '#BAE1FF',
                  '#E8BAFF', '#FFB3E6', '#C9BAFF', '#B3FFFF', '#FFE6B3']
        while len(colors) < len(labels):
            colors += colors
        ax = fig.add_subplot(111)
        ax.pie(values, labels=labels, colors=colors[:len(labels)],
               autopct='%1.1f%%', startangle=90, textprops={'fontsize': 8})
        title_map = {'expense': '支出', 'income': '收入'}
        ax.set_title(f"{year_month} {title_map.get(type_, type_)}分类占比", fontsize=10)
        ax.axis('equal')
        fig.tight_layout()
        self._attach_to_parent()
        return self.canvas


class AccountBalanceChart(_BaseChart):
    def __init__(self, acc_repo, parent=None, figsize=(6, 4)):
        super().__init__(parent, figsize)
        self.acc_repo = acc_repo

    def render(self):
        balances = self.acc_repo.get_balances()
        fig = self._new_figure()
        ax = fig.add_subplot(111)
        if not balances:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            fig.tight_layout()
            self._attach_to_parent()
            return self.canvas
        names = [b['name'] for b in balances]
        values = [b['current_balance'] for b in balances]
        colors = ['#45B7D1' if v >= 0 else '#FF6B6B' for v in values]
        ax.barh(range(len(names)), values, color=colors, alpha=0.8)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names)
        ax.invert_yaxis()
        ax.set_xlabel('余额 (¥)')
        ax.set_title('账户余额概览', fontsize=10)
        ax.axvline(0, color='black', linewidth=0.5)
        ax.tick_params(axis='both', labelsize=8)
        for i, v in enumerate(values):
            ax.text(v, i, f' ¥{v:,.0f}', va='center', fontsize=8)
        fig.tight_layout()
        self._attach_to_parent()
        return self.canvas


class SummaryTable:
    def __init__(self, tx_repo, cat_repo):
        self.tx_repo = tx_repo
        self.cat_repo = cat_repo

    def build(self, year_month):
        income_cats = self.tx_repo.get_category_income_summary(year_month)
        expense_cats = self.tx_repo.get_category_expense_summary_with_parent(year_month)

        total_income = sum(i['total'] for i in income_cats)
        total_expense = sum(e['total'] for e in expense_cats)

        income_data = []
        for inc in income_cats:
            pct = (inc['total'] / total_income * 100) if total_income > 0 else 0
            income_data.append({
                'category_id': inc['id'],
                'category': f"{inc.get('icon', '')} {inc['name']}",
                'amount': inc['total'],
                'percentage': pct
            })

        expense_parents = {}
        expense_subs_map = {}
        for exp in expense_cats:
            pid = exp.get('parent_id')
            if pid is None:
                expense_parents[exp['id']] = exp
            else:
                if pid not in expense_subs_map:
                    expense_subs_map[pid] = []
                expense_subs_map[pid].append(exp)

        expense_result = []
        for pid, parent in expense_parents.items():
            parent_total = parent['total']
            subs = expense_subs_map.get(pid, [])
            sub_sum = sum(s['total'] for s in subs)
            if subs and sub_sum > 0 and abs(parent_total - sub_sum) > 0.01:
                direct = parent_total - sub_sum
                subs_list = [{'id': s['id'], 'icon': s.get('icon', ''), 'name': s['name'], 'amount': s['total']} for s in subs]
                if direct > 0.01:
                    subs_list.insert(0, {'id': None, 'icon': '•', 'name': '其他', 'amount': direct})
            else:
                subs_list = [{'id': s['id'], 'icon': s.get('icon', ''), 'name': s['name'], 'amount': s['total']} for s in subs]
            pct = (parent_total / total_expense * 100) if total_expense > 0 else 0
            expense_result.append({
                'category_id': pid,
                'category': f"{parent.get('icon', '')} {parent['name']}",
                'amount': parent_total,
                'percentage': pct,
                'subs': subs_list
            })
        expense_result.sort(key=lambda x: x['amount'], reverse=True)

        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'income_data': income_data,
            'expense_data': expense_result
        }


class ExportService:
    def __init__(self, tx_repo, cat_repo, acc_repo):
        self.tx_repo = tx_repo
        self.cat_repo = cat_repo
        self.acc_repo = acc_repo
        self.table = SummaryTable(tx_repo, cat_repo)

    def export_monthly_csv(self, year_month, output_path):
        year_month = DatabaseConnection.normalize_year_month(year_month)
        transactions = self.tx_repo.find()
        month_txns = [t for t in transactions
                      if t.get('date', '').startswith(year_month)]

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['日期', '类型', '分类', '子分类', '账户', '金额', '备注'])
            for t in month_txns:
                if t['type'] == 'transfer':
                    type_str = '转账'
                    cat_str = ''
                    sub_cat_str = ''
                    acc_str = f"{t.get('account_name', '')}→{t.get('to_account_name', '')}"
                else:
                    type_str = '收入' if t['type'] == 'income' else '支出'
                    cat_icon = t.get('category_icon', '')
                    cat_name = t.get('category_name', '')
                    cat_str = f'{cat_icon} {cat_name}' if cat_name else '未分类'
                    sub_cat_str = ''
                    acc_str = t.get('account_name', '')
                writer.writerow([
                    t.get('date', ''),
                    type_str,
                    cat_str,
                    sub_cat_str,
                    acc_str,
                    f"{t.get('amount', 0):.2f}",
                    t.get('note', '')
                ])
        return os.path.abspath(output_path)

    def export_category_summary_csv(self, year_month, output_path):
        year_month = DatabaseConnection.normalize_year_month(year_month)
        summary = self.table.build(year_month)
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([f'{year_month} 分类收支汇总'])
            writer.writerow([])
            writer.writerow(['收入分类汇总'])
            writer.writerow(['分类', '金额', '占比(%)'])
            for item in summary['income_data']:
                writer.writerow([item['category'], f"{item['amount']:.2f}", f"{item['percentage']:.2f}"])
            writer.writerow(['收入合计', f"{summary['total_income']:.2f}", '100.00'])
            writer.writerow([])
            writer.writerow(['支出分类汇总'])
            writer.writerow(['分类', '金额', '占比(%)'])
            for item in summary['expense_data']:
                writer.writerow([item['category'], f"{item['amount']:.2f}", f"{item['percentage']:.2f}"])
                for sub in item.get('subs', []):
                    writer.writerow([f"  └ {sub['icon']} {sub['name']}", f"{sub['amount']:.2f}", ''])
            writer.writerow(['支出合计', f"{summary['total_expense']:.2f}", '100.00'])
            writer.writerow([])
            writer.writerow(['本月结余', f"{summary['balance']:.2f}"])
        return os.path.abspath(output_path)
