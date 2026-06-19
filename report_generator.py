import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datastore import DataStore


plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class ReportGenerator:
    COLORS = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
        '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
        '#F8B500', '#00CED1', '#FF69B4', '#32CD32'
    ]

    ACCOUNT_TYPE_ICONS = {
        'cash': '💵', 'bank': '🏦', 'credit': '💳',
        'alipay': '支付宝', 'wechat': '微信'
    }

    def __init__(self, datastore: DataStore):
        self.ds = datastore

    def get_monthly_summary(self, year_month):
        return self.ds.get_monthly_summary(year_month)

    def get_category_expense_summary(self, year_month):
        return self.ds.get_category_expense_summary(year_month)

    def get_category_expense_summary_with_parent(self, year_month):
        return self.ds.get_category_expense_summary_with_parent(year_month)

    def get_category_income_summary(self, year_month):
        return self.ds.get_category_income_summary(year_month)

    def get_monthly_trend(self, months=6):
        return self.ds.get_monthly_trend(months)

    def get_account_balances(self):
        return self.ds.get_account_balances()

    def create_expense_pie_chart(self, parent, year_month, figsize=(5, 4)):
        categories = self.get_category_expense_summary(year_month)
        parent_only = [c for c in categories if c['parent_id'] is None]

        fig = Figure(figsize=figsize, dpi=100, facecolor='white')
        ax = fig.add_subplot(111)

        if not parent_only:
            ax.text(0.5, 0.5, '暂无支出数据', ha='center', va='center',
                    fontsize=14, transform=ax.transAxes)
            ax.set_axis_off()
        else:
            labels = [f"{c['icon']} {c['name']}" for c in parent_only]
            sizes = [c['total'] for c in parent_only]
            colors = self.COLORS[:len(parent_only)]

            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                colors=colors,
                autopct='%1.1f%%',
                startangle=90,
                pctdistance=0.85,
                wedgeprops=dict(width=0.4, edgecolor='w')
            )

            for text in texts:
                text.set_fontsize(9)
            for autotext in autotexts:
                autotext.set_fontsize(8)
                autotext.set_color('white')

            ax.set_title(f'{year_month} 支出分类占比', fontsize=12, pad=15)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        return canvas

    def create_income_expense_bar_chart(self, parent, months=6, figsize=(6, 4)):
        trend = self.get_monthly_trend(months)

        fig = Figure(figsize=figsize, dpi=100, facecolor='white')
        ax = fig.add_subplot(111)

        if not trend:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center',
                    fontsize=14, transform=ax.transAxes)
            ax.set_axis_off()
        else:
            months_labels = [t['month'] for t in trend]
            income_values = [t['income'] for t in trend]
            expense_values = [t['expense'] for t in trend]

            import numpy as np
            x = np.arange(len(months_labels))
            width = 0.35

            bars1 = ax.bar(x - width/2, income_values, width,
                           label='收入', color='#4ECDC4')
            bars2 = ax.bar(x + width/2, expense_values, width,
                           label='支出', color='#FF6B6B')

            ax.set_xticks(x)
            ax.set_xticklabels(months_labels, rotation=45, ha='right', fontsize=9)
            ax.set_ylabel('金额 (元)', fontsize=10)
            ax.set_title(f'近{len(months_labels)}个月收支趋势', fontsize=12, pad=15)
            ax.legend(fontsize=9)
            ax.grid(axis='y', alpha=0.3)

            for bar in bars1:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                            f'{height:.0f}', ha='center', va='bottom', fontsize=7)

            for bar in bars2:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                            f'{height:.0f}', ha='center', va='bottom', fontsize=7)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        return canvas

    def create_account_balance_chart(self, parent, figsize=(5, 3)):
        accounts = self.get_account_balances()

        fig = Figure(figsize=figsize, dpi=100, facecolor='white')
        ax = fig.add_subplot(111)

        if not accounts:
            ax.text(0.5, 0.5, '暂无账户数据', ha='center', va='center',
                    fontsize=14, transform=ax.transAxes)
            ax.set_axis_off()
        else:
            import numpy as np
            names = [a['name'] for a in accounts]
            balances = [a['current_balance'] for a in accounts]
            colors = ['#4ECDC4' if b >= 0 else '#FF6B6B' for b in balances]

            y = np.arange(len(names))
            bars = ax.barh(y, balances, color=colors, height=0.5)

            ax.set_yticks(y)
            ax.set_yticklabels(names, fontsize=10)
            ax.set_xlabel('余额 (元)', fontsize=10)
            ax.set_title('账户余额', fontsize=12, pad=15)
            ax.grid(axis='x', alpha=0.3)
            ax.axvline(x=0, color='gray', linewidth=0.5)

            for bar, balance in zip(bars, balances):
                width = bar.get_width()
                label_x = width + max(abs(min(balances)), abs(max(balances))) * 0.02 if width >= 0 else width - max(abs(min(balances)), abs(max(balances))) * 0.02
                ax.text(label_x, bar.get_y() + bar.get_height()/2,
                        f'¥{balance:,.2f}', ha='left' if width >= 0 else 'right',
                        va='center', fontsize=9)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        return canvas

    def create_category_summary_table_data(self, year_month):
        expense_data = self.get_category_expense_summary_with_parent(year_month)
        income_categories = self.get_category_income_summary(year_month)

        total_income = sum(c['total'] for c in income_categories)
        total_expense = sum(c['total'] for c in expense_data)

        expense_grouped = {}
        for c in expense_data:
            parent_name = c.get('parent_name') or c['name']
            parent_icon = c.get('parent_icon') or c['icon']
            if parent_name not in expense_grouped:
                expense_grouped[parent_name] = {
                    'icon': parent_icon,
                    'total': 0,
                    'subs': []
                }
            expense_grouped[parent_name]['total'] += c['total']
            if c['parent_id'] is not None:
                expense_grouped[parent_name]['subs'].append({
                    'name': c['name'],
                    'icon': c['icon'],
                    'amount': c['total']
                })

        expense_result = []
        for parent_name, data in expense_grouped.items():
            pct = (data['total'] / total_expense * 100) if total_expense > 0 else 0
            expense_result.append({
                'category': f"{data['icon']} {parent_name}",
                'amount': data['total'],
                'percentage': pct,
                'subs': data['subs']
            })
        expense_result.sort(key=lambda x: x['amount'], reverse=True)

        income_data = []
        for c in income_categories:
            pct = (c['total'] / total_income * 100) if total_income > 0 else 0
            income_data.append({
                'category': f"{c['icon']} {c['name']}",
                'amount': c['total'],
                'percentage': pct
            })

        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'income_data': income_data,
            'expense_data': expense_result
        }
