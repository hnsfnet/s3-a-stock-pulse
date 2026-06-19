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

    def __init__(self, datastore: DataStore):
        self.ds = datastore

    def get_monthly_summary(self, year_month):
        return self.ds.get_monthly_summary(year_month)

    def get_category_expense_summary(self, year_month):
        return self.ds.get_category_expense_summary(year_month)

    def get_category_income_summary(self, year_month):
        return self.ds.get_category_income_summary(year_month)

    def get_monthly_trend(self, months=6):
        return self.ds.get_monthly_trend(months)

    def create_expense_pie_chart(self, parent, year_month, figsize=(5, 4)):
        categories = self.get_category_expense_summary(year_month)

        fig = Figure(figsize=figsize, dpi=100, facecolor='white')
        ax = fig.add_subplot(111)

        if not categories:
            ax.text(0.5, 0.5, '暂无支出数据', ha='center', va='center',
                    fontsize=14, transform=ax.transAxes)
            ax.set_axis_off()
        else:
            labels = [f"{c['icon']} {c['name']}" for c in categories]
            sizes = [c['total'] for c in categories]
            colors = self.COLORS[:len(categories)]

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

    def create_category_summary_table_data(self, year_month):
        expense_categories = self.get_category_expense_summary(year_month)
        income_categories = self.get_category_income_summary(year_month)

        total_income = sum(c['total'] for c in income_categories)
        total_expense = sum(c['total'] for c in expense_categories)

        expense_data = []
        for c in expense_categories:
            pct = (c['total'] / total_expense * 100) if total_expense > 0 else 0
            expense_data.append({
                'category': f"{c['icon']} {c['name']}",
                'amount': c['total'],
                'percentage': pct
            })

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
            'expense_data': expense_data
        }
