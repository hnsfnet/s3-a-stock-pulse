import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date, timedelta

from config import config
from datastore import DataStore
from ledger import Ledger
from budget_manager import BudgetManager
from report_generator import ReportGenerator
from logger import get_logger

logger = get_logger('app')

ctk.set_appearance_mode(config.get('app.theme', 'light'))
ctk.set_default_color_theme(config.get('app.color_theme', 'blue'))

ACCOUNT_TYPE_LABELS = {
    'cash': '现金', 'bank': '银行卡', 'credit': '信用卡',
    'alipay': '支付宝', 'wechat': '微信'
}

ACCOUNT_TYPE_ICONS = {
    'cash': '💵', 'bank': '🏦', 'credit': '💳', 'alipay': '📱', 'wechat': '💬'
}

FREQUENCY_LABELS = {
    'daily': '每天', 'weekly': '每周', 'monthly': '每月', 'yearly': '每年'
}


def _build_category_display(categories):
    result = []
    for c in categories:
        if c.get('parent_id') is None:
            result.append((c, f"{c['icon']} {c['name']}"))
    return result


def _find_category_by_display(categories, display_str):
    for c in categories:
        if f"{c['icon']} {c['name']}" == display_str:
            return c
    return None


class Page:
    def __init__(self, master=None, **kwargs):
        self._master = master
        self._kwargs = kwargs
        self.ledger = kwargs.get('ledger')
        self.budget_manager = kwargs.get('budget_manager')
        self.report_generator = kwargs.get('report_generator')
        self.refresh_callback = kwargs.get('refresh_callback')

    def build(self):
        raise NotImplementedError

    def refresh(self):
        pass

    def on_show(self):
        self.refresh()


class PageRouter:
    def __init__(self):
        self._pages = {}
        self._builders = {}

    def register(self, key, page_class, **static_kwargs):
        self._builders[key] = (page_class, static_kwargs)

    def show(self, key, master, **runtime_kwargs):
        for w in master.winfo_children():
            w.destroy()
        page_cls, static_kw = self._builders[key]
        merged = {**static_kw, **runtime_kwargs}
        page = page_cls(master, **merged)
        self._pages[key] = page
        if hasattr(page, 'build') and callable(page.build):
            try:
                page.build()
            except Exception:
                pass
        if hasattr(page, 'on_show') and callable(page.on_show):
            try:
                page.on_show()
            except Exception:
                pass
        return page

    def refresh_all(self, key, master, **runtime_kwargs):
        if key in self._pages:
            del self._pages[key]
        return self.show(key, master, **runtime_kwargs)


class App(ctk.CTk):
    PAGE_REGISTRY = [
        ('overview', '📊 概览'),
        ('transactions', '📝 交易明细'),
        ('accounts', '💳 账户管理'),
        ('budget', '🎯 预算管理'),
        ('recurring', '🔁 周期记账'),
        ('report', '📈 报表统计'),
    ]

    def __init__(self):
        super().__init__()
        app_name = config.get('app.name', 'StockPulse 记账')
        self.title(app_name)
        window_size = config.get('app.window_size', [1000, 700])
        self.geometry(f'{window_size[0]}x{window_size[1]}')
        self.minsize(900, 600)

        logger.info(f"Starting {app_name}...")

        self.ds = DataStore()
        self.ledger = Ledger(self.ds)
        self.budget_manager = BudgetManager(self.ds)
        self.report_generator = ReportGenerator(self.ds)
        logger.info("Core modules initialized")

        generated = self.ledger.process_due_recurring()
        if generated > 0:
            logger.info(f"Auto-generated {generated} recurring transactions")
            messagebox.showinfo('周期记账', f'已自动生成 {generated} 笔到期的周期性交易记录。')

        self.current_page = 'overview'
        self.current_month = self.ledger.get_current_month_str()

        self._buttons = {}
        self.router = PageRouter()
        self.router.register('overview', OverviewPage,
                             ledger=self.ledger, budget_manager=self.budget_manager,
                             report_generator=self.report_generator)
        self.router.register('transactions', TransactionsPage,
                             ledger=self.ledger, refresh_callback=self._refresh_all)
        self.router.register('accounts', AccountsPage,
                             ledger=self.ledger, refresh_callback=self._refresh_all)
        self.router.register('budget', BudgetPage,
                             budget_manager=self.budget_manager, ledger=self.ledger,
                             refresh_callback=self._refresh_all)
        self.router.register('recurring', RecurringRulesPage,
                             ledger=self.ledger, refresh_callback=self._refresh_all)
        self.router.register('report', ReportPage,
                             report_generator=self.report_generator)

        self._create_sidebar()
        self._create_main_area()
        self._show_page('overview')
        logger.info(f"{app_name} started successfully")

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=180, corner_radius=0)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        logo_label = ctk.CTkLabel(
            self.sidebar,
            text='💰 记账本',
            font=ctk.CTkFont(size=20, weight='bold')
        )
        logo_label.pack(pady=30)

        for key, label in self.PAGE_REGISTRY:
            btn = self._create_sidebar_button(label, lambda k=key: self._show_page(k))
            btn.pack(pady=5, padx=10, fill='x')
            self._buttons[key] = btn

    def _create_sidebar_button(self, text, command):
        return ctk.CTkButton(
            self.sidebar,
            text=text,
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color='transparent',
            text_color=('gray10', 'gray90'),
            hover_color=('gray70', 'gray30'),
            anchor='w',
            command=command
        )

    def _update_sidebar_active(self, active_key):
        for key, btn in self._buttons.items():
            btn.configure(fg_color='transparent', text_color=('gray10', 'gray90'))
        if active_key in self._buttons:
            self._buttons[active_key].configure(fg_color=('#3B8ED0', '#1F6AA5'), text_color='white')

    def _create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.pack(side='right', fill='both', expand=True)
        self.main_frame.pack_propagate(False)

    def _show_page(self, key):
        self.current_page = key
        self._update_sidebar_active(key)
        self.router.show(key, self.main_frame)

    def _refresh_all(self):
        self.router.refresh_all(self.current_page, self.main_frame)

    def destroy(self):
        self.ds.close()
        super().destroy()


class OverviewPage(ctk.CTkScrollableFrame, Page):
    def __init__(self, master, ledger=None, budget_manager=None, report_generator=None, **kwargs):
        ctk.CTkScrollableFrame.__init__(self, master, corner_radius=0)
        Page.__init__(self, master, ledger=ledger, budget_manager=budget_manager,
                      report_generator=report_generator, **kwargs)
        self.ledger = ledger
        self.budget_manager = budget_manager
        self.report_generator = report_generator
        self.current_month = self.ledger.get_current_month_str()
        self.pack(fill='both', expand=True)

        self._create_header()
        self._create_summary_cards()
        self._create_account_balances()
        self._create_chart_and_recent()

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=20, pady=(20, 10))

        title = ctk.CTkLabel(
            header,
            text=f'📊 {self.current_month} 概览',
            font=ctk.CTkFont(size=24, weight='bold')
        )
        title.pack(side='left')

    def _create_summary_cards(self):
        summary = self.ledger.get_monthly_summary(self.current_month)
        budget_status = self.budget_manager.get_total_budget_status(self.current_month)

        cards_frame = ctk.CTkFrame(self, fg_color='transparent')
        cards_frame.pack(fill='x', padx=20, pady=10)

        self._create_card(cards_frame, '💰 总收入', f'¥{summary["total_income"]:,.2f}', '#4ECDC4', 0, 0)
        self._create_card(cards_frame, '💸 总支出', f'¥{summary["total_expense"]:,.2f}', '#FF6B6B', 0, 1)
        self._create_card(cards_frame, '📈 结余', f'¥{summary["balance"]:,.2f}', '#45B7D1', 0, 2)
        self._create_card(cards_frame, '🎯 预算剩余', f'¥{budget_status["remaining"]:,.2f}',
                          '#96CEB4', 0, 3)

        cards_frame.grid_columnconfigure(0, weight=1)
        cards_frame.grid_columnconfigure(1, weight=1)
        cards_frame.grid_columnconfigure(2, weight=1)
        cards_frame.grid_columnconfigure(3, weight=1)

    def _create_card(self, parent, title, value, color, row, col):
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color='white',
                            border_width=2, border_color=color)
        card.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')

        title_label = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=13), text_color='gray')
        title_label.pack(pady=(15, 5), padx=15, anchor='w')

        value_label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=22, weight='bold'),
                                   text_color=color)
        value_label.pack(pady=(0, 15), padx=15, anchor='w')

    def _create_account_balances(self):
        accounts = self.ledger.get_account_balances()
        if not accounts:
            return

        section = ctk.CTkFrame(self, corner_radius=10, fg_color='white')
        section.pack(fill='x', padx=20, pady=10)

        header = ctk.CTkFrame(section, fg_color='transparent')
        header.pack(fill='x', padx=15, pady=(15, 5))

        title = ctk.CTkLabel(header, text='💳 账户余额',
                             font=ctk.CTkFont(size=16, weight='bold'))
        title.pack(side='left')

        total_assets = sum(a['current_balance'] for a in accounts)
        total_label = ctk.CTkLabel(
            header,
            text=f'总资产: ¥{total_assets:,.2f}',
            font=ctk.CTkFont(size=14, weight='bold'),
            text_color='#45B7D1'
        )
        total_label.pack(side='right')

        cards_frame = ctk.CTkFrame(section, fg_color='transparent')
        cards_frame.pack(fill='x', padx=15, pady=(0, 15))

        n = len(accounts)
        for i, acc in enumerate(accounts):
            self._create_account_balance_card(cards_frame, acc, i, n)
        for i in range(n):
            cards_frame.grid_columnconfigure(i, weight=1)

    def _create_account_balance_card(self, parent, acc, index, total):
        icon = ACCOUNT_TYPE_ICONS.get(acc['type'], '💰')
        balance = acc['current_balance']
        color = '#4ECDC4' if balance >= 0 else '#FF6B6B'

        card = ctk.CTkFrame(parent, corner_radius=8, fg_color='#F8F9FA',
                            border_width=1, border_color='#E0E0E0')
        card.grid(row=0, column=index, padx=8, pady=5, sticky='nsew')

        name_label = ctk.CTkLabel(card, text=f"{icon} {acc['name']}",
                                  font=ctk.CTkFont(size=13, weight='bold'))
        name_label.pack(pady=(10, 2), padx=10)

        bal_label = ctk.CTkLabel(card, text=f'¥{balance:,.2f}',
                                 font=ctk.CTkFont(size=18, weight='bold'),
                                 text_color=color)
        bal_label.pack(pady=(0, 10), padx=10)

    def _create_chart_and_recent(self):
        content_frame = ctk.CTkFrame(self, fg_color='transparent')
        content_frame.pack(fill='both', expand=True, padx=20, pady=10)

        left_frame = ctk.CTkFrame(content_frame, corner_radius=10, fg_color='white')
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        chart_title = ctk.CTkLabel(left_frame, text='🥧 分类支出占比',
                                   font=ctk.CTkFont(size=16, weight='bold'))
        chart_title.pack(pady=15, padx=15, anchor='w')

        chart_canvas = self.report_generator.create_expense_pie_chart(
            left_frame, self.current_month, figsize=(5, 4))
        chart_canvas.get_tk_widget().pack(padx=15, pady=(0, 15))

        right_frame = ctk.CTkFrame(content_frame, corner_radius=10, fg_color='white')
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))

        recent_title = ctk.CTkLabel(right_frame, text='📋 最近交易',
                                    font=ctk.CTkFont(size=16, weight='bold'))
        recent_title.pack(pady=15, padx=15, anchor='w')

        transactions = self.ledger.get_recent_transactions(10)
        self._create_recent_list(right_frame, transactions)

    def _create_recent_list(self, parent, transactions):
        list_frame = ctk.CTkScrollableFrame(parent, fg_color='transparent', height=350)
        list_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        if not transactions:
            empty_label = ctk.CTkLabel(list_frame, text='暂无交易记录', text_color='gray')
            empty_label.pack(pady=30)
            return

        for txn in transactions:
            self._create_transaction_item(list_frame, txn)

    def _create_transaction_item(self, parent, txn):
        item = ctk.CTkFrame(parent, fg_color='transparent')
        item.pack(fill='x', pady=5)

        if txn['type'] == 'income':
            icon_bg, icon_color, amount_prefix = '#E8F8F5', '#4ECDC4', '+'
        elif txn['type'] == 'transfer':
            icon_bg, icon_color, amount_prefix = '#E8F0FE', '#45B7D1', '↔'
        else:
            icon_bg, icon_color, amount_prefix = '#FDF2F2', '#FF6B6B', '-'

        if txn['type'] == 'transfer':
            cat_icon = '🔄'
            cat_name = f"转账 {txn['account_name']}→{txn.get('to_account_name') or '?'}"
        else:
            cat_icon = txn['category_icon'] or '📦'
            cat_name = txn['category_name'] or '未分类'

        icon_frame = ctk.CTkFrame(item, width=40, height=40, corner_radius=20,
                                  fg_color=icon_bg)
        icon_frame.pack(side='left')
        icon_frame.pack_propagate(False)

        icon_label = ctk.CTkLabel(icon_frame, text=cat_icon,
                                  font=ctk.CTkFont(size=18))
        icon_label.pack(expand=True)

        info_frame = ctk.CTkFrame(item, fg_color='transparent')
        info_frame.pack(side='left', fill='x', expand=True, padx=10)

        top_row = ctk.CTkFrame(info_frame, fg_color='transparent')
        top_row.pack(fill='x')

        category_label = ctk.CTkLabel(top_row, text=cat_name,
                                      font=ctk.CTkFont(size=14, weight='bold'))
        category_label.pack(side='left')

        amount_label = ctk.CTkLabel(top_row, text=f'{amount_prefix}¥{txn["amount"]:,.2f}',
                                    font=ctk.CTkFont(size=14, weight='bold'),
                                    text_color=icon_color)
        amount_label.pack(side='right')

        bottom_row = ctk.CTkFrame(info_frame, fg_color='transparent')
        bottom_row.pack(fill='x', pady=(2, 0))

        date_label = ctk.CTkLabel(bottom_row, text=txn['date'], text_color='gray',
                                  font=ctk.CTkFont(size=12))
        date_label.pack(side='left')

        account_label = ctk.CTkLabel(bottom_row, text=txn['account_name'], text_color='gray',
                                     font=ctk.CTkFont(size=12))
        account_label.pack(side='right')

        if txn['note']:
            note_label = ctk.CTkLabel(info_frame, text=txn['note'], text_color='gray',
                                      font=ctk.CTkFont(size=11))
            note_label.pack(anchor='w', pady=(2, 0))

        separator = ctk.CTkFrame(parent, height=1, fg_color=('#E0E0E0', '#404040'))
        separator.pack(fill='x', pady=5)


class TransactionsPage(ctk.CTkFrame, Page):
    def __init__(self, master, ledger=None, refresh_callback=None, **kwargs):
        ctk.CTkFrame.__init__(self, master, corner_radius=0, fg_color='transparent')
        Page.__init__(self, master, ledger=ledger, refresh_callback=refresh_callback, **kwargs)
        self.ledger = ledger
        self.refresh_callback = refresh_callback
        self.pack(fill='both', expand=True)

        self._create_header()
        self._create_filters()
        self._create_transactions_list()

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=20, pady=(20, 10))

        title = ctk.CTkLabel(
            header,
            text='📝 交易明细',
            font=ctk.CTkFont(size=24, weight='bold')
        )
        title.pack(side='left')

        add_btn = ctk.CTkButton(
            header,
            text='+ 新增交易',
            font=ctk.CTkFont(size=14),
            height=40,
            command=self._open_add_dialog
        )
        add_btn.pack(side='right')

        transfer_btn = ctk.CTkButton(
            header,
            text='🔁 新增转账',
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color='#45B7D1',
            command=self._open_transfer_dialog
        )
        transfer_btn.pack(side='right', padx=(0, 10))

    def _create_filters(self):
        filter_frame = ctk.CTkFrame(self, corner_radius=10, fg_color='white')
        filter_frame.pack(fill='x', padx=20, pady=10)

        date_start_label = ctk.CTkLabel(filter_frame, text='开始日期:')
        date_start_label.pack(side='left', padx=(15, 5), pady=15)

        self.date_start_var = ctk.StringVar()
        date_start_entry = ctk.CTkEntry(filter_frame, width=120, textvariable=self.date_start_var,
                                        placeholder_text='YYYY-MM-DD')
        date_start_entry.pack(side='left', padx=5, pady=15)

        date_end_label = ctk.CTkLabel(filter_frame, text='结束日期:')
        date_end_label.pack(side='left', padx=(10, 5), pady=15)

        self.date_end_var = ctk.StringVar()
        date_end_entry = ctk.CTkEntry(filter_frame, width=120, textvariable=self.date_end_var,
                                      placeholder_text='YYYY-MM-DD')
        date_end_entry.pack(side='left', padx=5, pady=15)

        type_label = ctk.CTkLabel(filter_frame, text='类型:')
        type_label.pack(side='left', padx=(10, 5), pady=15)

        self.type_var = ctk.StringVar(value='全部')
        type_combo = ctk.CTkComboBox(filter_frame, values=['全部', '收入', '支出', '转账'],
                                     variable=self.type_var, width=80,
                                     command=lambda e: self._on_filter_change())
        type_combo.pack(side='left', padx=5, pady=15)

        cat_label = ctk.CTkLabel(filter_frame, text='分类:')
        cat_label.pack(side='left', padx=(10, 5), pady=15)

        self.category_var = ctk.StringVar(value='全部分类')
        categories = self.ledger.get_categories()
        cat_values = ['全部分类'] + [f"{c['icon']} {c['name']}" for c in categories]
        self.category_combo = ctk.CTkComboBox(filter_frame, values=cat_values,
                                              variable=self.category_var, width=120,
                                              command=lambda e: self._on_filter_change())
        self.category_combo.pack(side='left', padx=5, pady=15)

        acc_label = ctk.CTkLabel(filter_frame, text='账户:')
        acc_label.pack(side='left', padx=(10, 5), pady=15)

        self.account_var = ctk.StringVar(value='全部账户')
        accounts = self.ledger.get_accounts()
        acc_values = ['全部账户'] + [a['name'] for a in accounts]
        acc_combo = ctk.CTkComboBox(filter_frame, values=acc_values,
                                    variable=self.account_var, width=100,
                                    command=lambda e: self._on_filter_change())
        acc_combo.pack(side='left', padx=5, pady=15)

        search_label = ctk.CTkLabel(filter_frame, text='搜索:')
        search_label.pack(side='left', padx=(10, 5), pady=15)

        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(filter_frame, width=150, textvariable=self.search_var,
                                    placeholder_text='备注关键字')
        search_entry.pack(side='left', padx=5, pady=15)
        search_entry.bind('<KeyRelease>', lambda e: self._on_filter_change())

        filter_btn = ctk.CTkButton(filter_frame, text='筛选', width=60,
                                   command=self._on_filter_change)
        filter_btn.pack(side='right', padx=(5, 15), pady=15)

        reset_btn = ctk.CTkButton(filter_frame, text='重置', width=60,
                                  fg_color='gray', command=self._reset_filters)
        reset_btn.pack(side='right', padx=5, pady=15)

    def _on_filter_change(self):
        self._refresh_list()

    def _reset_filters(self):
        self.date_start_var.set('')
        self.date_end_var.set('')
        self.type_var.set('全部')
        self.category_var.set('全部分类')
        self.account_var.set('全部账户')
        self.search_var.set('')
        self._refresh_list()

    def _create_transactions_list(self):
        list_frame = ctk.CTkFrame(self, corner_radius=10, fg_color='white')
        list_frame.pack(fill='both', expand=True, padx=20, pady=(10, 20))

        columns = ('date', 'type', 'category', 'account', 'amount', 'note', 'actions')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        self.tree.heading('date', text='日期')
        self.tree.heading('type', text='类型')
        self.tree.heading('category', text='分类')
        self.tree.heading('account', text='账户')
        self.tree.heading('amount', text='金额')
        self.tree.heading('note', text='备注')
        self.tree.heading('actions', text='操作')

        self.tree.column('date', width=100, anchor='center')
        self.tree.column('type', width=60, anchor='center')
        self.tree.column('category', width=80, anchor='center')
        self.tree.column('account', width=80, anchor='center')
        self.tree.column('amount', width=100, anchor='e')
        self.tree.column('note', width=200, anchor='w')
        self.tree.column('actions', width=100, anchor='center')

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True, padx=(15, 0), pady=15)
        scrollbar.pack(side='right', fill='y', padx=(0, 15), pady=15)

        self.tree.bind('<Double-1>', self._on_row_double_click)

        self._refresh_list()

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        type_map = {'收入': 'income', '支出': 'expense', '转账': 'transfer'}
        type_ = type_map.get(self.type_var.get())

        category_id = None
        cat_display = self.category_var.get()
        if cat_display != '全部分类':
            categories = self.ledger.get_categories()
            cat = _find_category_by_display(categories, cat_display)
            if cat:
                category_id = cat['id']

        account_id = None
        acc_name = self.account_var.get()
        if acc_name != '全部账户':
            for a in self.ledger.get_accounts():
                if a['name'] == acc_name:
                    account_id = a['id']
                    break

        keyword = self.search_var.get() if self.search_var.get() else None
        start_date = self.date_start_var.get() if self.date_start_var.get() else None
        end_date = self.date_end_var.get() if self.date_end_var.get() else None

        transactions = self.ledger.list_transactions(
            start_date=start_date,
            end_date=end_date,
            type_=type_,
            category_id=category_id,
            account_id=account_id,
            keyword=keyword
        )

        for txn in transactions:
            if txn['type'] == 'transfer':
                type_text = '转账'
                amount_text = f'¥{txn["amount"]:,.2f}'
                category_text = f"🔄 {txn['account_name']}→{txn.get('to_account_name') or '?'}"
            else:
                type_text = '收入' if txn['type'] == 'income' else '支出'
                prefix = '+' if txn['type'] == 'income' else '-'
                amount_text = f'{prefix}¥{txn["amount"]:,.2f}'
                category_text = f"{txn.get('category_icon') or '📦'} {txn.get('category_name') or '未分类'}"
            self.tree.insert('', 'end', iid=str(txn['id']),
                             values=(txn['date'], type_text, category_text,
                                     txn['account_name'], amount_text, txn['note'], '编辑/删除'))

    def _on_row_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            txn_id = int(item)
            self._open_edit_dialog(txn_id)

    def _open_add_dialog(self):
        TransactionDialog(self, self.ledger, None, self._on_transaction_saved, mode='normal')

    def _open_transfer_dialog(self):
        TransactionDialog(self, self.ledger, None, self._on_transaction_saved, mode='transfer')

    def _open_edit_dialog(self, txn_id):
        TransactionDialog(self, self.ledger, txn_id, self._on_transaction_saved)

    def _on_transaction_saved(self):
        self.ledger.refresh_data()
        self._reset_filters()
        self._refresh_category_combo()
        self._refresh_account_combo()
        self._refresh_list()
        self.refresh_callback()

    def _refresh_category_combo(self):
        categories = self.ledger.get_categories()
        current_val = self.category_var.get()
        cat_values = ['全部分类'] + [f"{c['icon']} {c['name']}" for c in categories]
        self.category_combo.configure(values=cat_values)
        if current_val not in cat_values:
            self.category_var.set('全部分类')
        else:
            self.category_var.set(current_val)

    def _refresh_account_combo(self):
        accounts = self.ledger.get_accounts()
        current_val = self.account_var.get()
        acc_values = ['全部账户'] + [a['name'] for a in accounts]
        if current_val not in acc_values:
            self.account_var.set('全部账户')


class TransactionDialog(ctk.CTkToplevel):
    def __init__(self, master, ledger, txn_id, on_saved, mode='normal'):
        super().__init__(master)
        self.ledger = ledger
        self.txn_id = txn_id
        self.on_saved = on_saved
        self.mode = mode
        self.title('编辑交易' if txn_id else '新增交易')
        self.geometry('420x740')
        self.resizable(False, True)
        self.transient(master)
        self.grab_set()

        self.categories = self.ledger.get_categories()
        self.accounts = self.ledger.get_accounts()

        self._create_widgets()

        if txn_id:
            self._load_transaction()
        elif mode == 'transfer':
            self.type_var.set('transfer')
            self._on_type_change()

    def _create_widgets(self):
        main_frame = ctk.CTkScrollableFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text='类型', font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(10, 5))
        type_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        type_frame.pack(fill='x')
        self.type_var = ctk.StringVar(value='expense')
        ctk.CTkRadioButton(type_frame, text='支出', variable=self.type_var,
                           value='expense', command=self._on_type_change).pack(side='left', padx=(0, 20))
        ctk.CTkRadioButton(type_frame, text='收入', variable=self.type_var,
                           value='income', command=self._on_type_change).pack(side='left', padx=(0, 20))
        ctk.CTkRadioButton(type_frame, text='转账', variable=self.type_var,
                           value='transfer', command=self._on_type_change).pack(side='left')

        ctk.CTkLabel(main_frame, text='日期', font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
        self.date_var = ctk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        ctk.CTkEntry(main_frame, textvariable=self.date_var).pack(fill='x')

        ctk.CTkLabel(main_frame, text='金额', font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
        self.amount_var = ctk.StringVar()
        ctk.CTkEntry(main_frame, textvariable=self.amount_var, placeholder_text='请输入金额').pack(fill='x')

        self.detail_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        self.detail_frame.pack(fill='x')

        repeat_container = ctk.CTkFrame(main_frame, fg_color='transparent')
        repeat_container.pack(fill='x', pady=(20, 5))
        self.repeat_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(repeat_container, text='🔁 设置重复（周期性自动记账）',
                        variable=self.repeat_var, command=self._toggle_repeat).pack(anchor='w')
        self.repeat_frame = ctk.CTkFrame(repeat_container, fg_color='#F0F0F0', corner_radius=8)
        self._build_repeat_options()

        ctk.CTkLabel(main_frame, text='备注', font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
        self.note_text = ctk.CTkTextbox(main_frame, height=60)
        self.note_text.pack(fill='x')

        btn_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        btn_frame.pack(fill='x', pady=(25, 10))
        if self.txn_id:
            ctk.CTkButton(btn_frame, text='删除', fg_color='#FF6B6B',
                          width=80, command=self._on_delete).pack(side='left')
        ctk.CTkButton(btn_frame, text='取消', fg_color='gray',
                      width=80, command=self.destroy).pack(side='right')
        ctk.CTkButton(btn_frame, text='保存', width=80,
                      command=self._on_save).pack(side='right', padx=10)

        self._build_detail_section()

    def _build_repeat_options(self):
        ctk.CTkLabel(self.repeat_frame, text='重复频率',
                     font=ctk.CTkFont(size=13)).pack(anchor='w', padx=15, pady=(15, 5))
        self.freq_var = ctk.StringVar(value='每月')
        ctk.CTkComboBox(self.repeat_frame, values=['每天', '每周', '每月', '每年'],
                        variable=self.freq_var, state='readonly', width=120).pack(anchor='w', padx=15)

        ctk.CTkLabel(self.repeat_frame, text='间隔（每N个周期）',
                     font=ctk.CTkFont(size=13)).pack(anchor='w', padx=15, pady=(15, 5))
        self.interval_var = ctk.StringVar(value='1')
        ctk.CTkEntry(self.repeat_frame, textvariable=self.interval_var, width=80).pack(anchor='w', padx=15)

        ctk.CTkLabel(self.repeat_frame, text='结束日期（可选）',
                     font=ctk.CTkFont(size=13)).pack(anchor='w', padx=15, pady=(15, 5))
        self.end_date_var = ctk.StringVar()
        ctk.CTkEntry(self.repeat_frame, textvariable=self.end_date_var, width=150,
                     placeholder_text='YYYY-MM-DD').pack(anchor='w', padx=15)
        ctk.CTkLabel(self.repeat_frame, text='留空表示无限重复',
                     font=ctk.CTkFont(size=11), text_color='gray').pack(anchor='w', padx=15, pady=(2, 15))

    def _toggle_repeat(self):
        if self.repeat_var.get():
            self.repeat_frame.pack(fill='x', pady=5)
        else:
            self.repeat_frame.pack_forget()

    def _build_detail_section(self):
        for widget in self.detail_frame.winfo_children():
            widget.destroy()

        type_ = self.type_var.get()
        account_names = [a['name'] for a in self.accounts]

        if type_ == 'transfer':
            ctk.CTkLabel(self.detail_frame, text='转出账户',
                         font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
            self.from_account_var = ctk.StringVar()
            ctk.CTkComboBox(self.detail_frame, values=account_names,
                           variable=self.from_account_var, state='readonly').pack(fill='x')
            if account_names:
                self.from_account_var.set(account_names[0])

            ctk.CTkLabel(self.detail_frame, text='转入账户',
                         font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
            self.to_account_var = ctk.StringVar()
            ctk.CTkComboBox(self.detail_frame, values=account_names,
                           variable=self.to_account_var, state='readonly').pack(fill='x')
            if len(account_names) > 1:
                self.to_account_var.set(account_names[1])
            elif account_names:
                self.to_account_var.set(account_names[0])
        else:
            ctk.CTkLabel(self.detail_frame, text='分类',
                         font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
            self.category_var = ctk.StringVar()
            self.category_combo = ctk.CTkComboBox(self.detail_frame, values=[],
                                                  variable=self.category_var, state='readonly')
            self.category_combo.pack(fill='x')
            self._refresh_categories()

            ctk.CTkLabel(self.detail_frame, text='账户',
                         font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
            self.account_var = ctk.StringVar()
            ctk.CTkComboBox(self.detail_frame, values=account_names,
                           variable=self.account_var, state='readonly').pack(fill='x')
            if account_names:
                self.account_var.set(account_names[0])

    def _refresh_categories(self):
        if not hasattr(self, 'category_combo'):
            return
        type_ = self.type_var.get()
        cats = [c for c in self.categories if c['type'] == type_ and c.get('parent_id') is None]
        cat_display = [f"{c['icon']} {c['name']}" for c in cats]
        self.category_combo.configure(values=cat_display)
        if cat_display:
            self.category_var.set(cat_display[0])

    def _on_type_change(self):
        self._build_detail_section()

    def _load_transaction(self):
        txn = self.ledger.get_transaction(self.txn_id)
        if not txn:
            return
        self.type_var.set(txn['type'])
        self._build_detail_section()
        self.date_var.set(txn['date'])
        self.amount_var.set(str(txn['amount']))

        if txn['type'] == 'transfer':
            self.from_account_var.set(txn['account_name'])
            if txn.get('to_account_name'):
                self.to_account_var.set(txn['to_account_name'])
        else:
            category_display = f"{txn.get('category_icon') or '📦'} {txn.get('category_name') or '未分类'}"
            self.category_var.set(category_display)
            self.account_var.set(txn['account_name'])

        self.note_text.insert('1.0', txn.get('note') or '')

    def _get_account_id(self, name):
        for a in self.accounts:
            if a['name'] == name:
                return a['id']
        return None

    def _on_save(self):
        try:
            amount = float(self.amount_var.get())
        except ValueError:
            messagebox.showerror('错误', '请输入有效的金额')
            return
        if amount <= 0:
            messagebox.showerror('错误', '金额必须大于0')
            return

        date_str = self.date_var.get()
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror('错误', '日期格式不正确，请使用 YYYY-MM-DD 格式')
            return

        type_ = self.type_var.get()
        note = self.note_text.get('1.0', 'end').strip()

        if type_ == 'transfer':
            from_id = self._get_account_id(self.from_account_var.get())
            to_id = self._get_account_id(self.to_account_var.get())
            if from_id is None or to_id is None:
                messagebox.showerror('错误', '请选择转出和转入账户')
                return
            if from_id == to_id:
                messagebox.showerror('错误', '转出和转入账户不能相同')
                return
            try:
                if self.txn_id:
                    self.ledger.update_transaction(
                        self.txn_id, date_str, amount, 'transfer', None, from_id, note,
                        to_account_id=to_id
                    )
                else:
                    self.ledger.add_transaction(
                        date_str, amount, 'transfer', None, from_id, note, to_account_id=to_id
                    )
            except Exception as e:
                messagebox.showerror('错误', str(e))
                return
        else:
            cat_display = self.category_var.get()
            category_id = None
            for c in self.categories:
                if f"{c['icon']} {c['name']}" == cat_display:
                    category_id = c['id']
                    break
            if category_id is None:
                messagebox.showerror('错误', '请选择分类')
                return
            account_id = self._get_account_id(self.account_var.get())
            if account_id is None:
                messagebox.showerror('错误', '请选择账户')
                return
            try:
                if self.txn_id:
                    self.ledger.update_transaction(
                        self.txn_id, date_str, amount, type_, category_id, account_id, note
                    )
                else:
                    self.ledger.add_transaction(
                        date_str, amount, type_, category_id, account_id, note
                    )
            except Exception as e:
                messagebox.showerror('错误', str(e))
                return

        if self.repeat_var.get() and not self.txn_id:
            self._create_recurring_rule(date_str, amount, type_, note)

        self.on_saved()
        self.destroy()

    def _create_recurring_rule(self, date_str, amount, type_, note):
        freq_map = {'每天': 'daily', '每周': 'weekly', '每月': 'monthly', '每年': 'yearly'}
        frequency = freq_map.get(self.freq_var.get(), 'monthly')
        try:
            interval_val = int(self.interval_var.get())
        except ValueError:
            interval_val = 1
        if interval_val < 1:
            interval_val = 1

        end_date = self.end_date_var.get().strip()
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                messagebox.showwarning('提示', '结束日期格式不正确，已忽略结束日期')
                end_date = None

        category_id = None
        account_id = None
        to_account_id = None
        if type_ == 'transfer':
            account_id = self._get_account_id(self.from_account_var.get())
            to_account_id = self._get_account_id(self.to_account_var.get())
        else:
            cat_display = self.category_var.get()
            for c in self.categories:
                if f"{c['icon']} {c['name']}" == cat_display:
                    category_id = c['id']
                    break
            account_id = self._get_account_id(self.account_var.get())

        name = note[:20] if note else f'周期性{type_}'
        try:
            self.ledger.add_recurring_rule(
                name, frequency, interval_val, type_, amount,
                category_id, account_id, note, to_account_id=to_account_id,
                start_date=date_str, end_date=end_date
            )
            messagebox.showinfo('成功', '已创建周期性记账规则，将在到期时自动生成交易。')
        except Exception as e:
            messagebox.showerror('错误', f'创建周期规则失败: {e}')

    def _on_delete(self):
        if messagebox.askyesno('确认', '确定要删除这条交易记录吗？'):
            if self.ledger.delete_transaction(self.txn_id):
                self.on_saved()
                self.destroy()


class BudgetPage(ctk.CTkScrollableFrame, Page):
    def __init__(self, master, budget_manager=None, ledger=None, refresh_callback=None, **kwargs):
        ctk.CTkScrollableFrame.__init__(self, master, corner_radius=0)
        Page.__init__(self, master, budget_manager=budget_manager, ledger=ledger,
                      refresh_callback=refresh_callback, **kwargs)
        self.budget_manager = budget_manager
        self.ledger = ledger
        self.refresh_callback = refresh_callback
        self.current_month = self.budget_manager.get_current_month_str()
        self.pack(fill='both', expand=True)

        self._create_header()
        self._create_total_budget()
        self._create_category_budgets()
        self._create_warnings()

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=20, pady=(20, 10))

        title = ctk.CTkLabel(
            header,
            text=f'🎯 {self.current_month} 预算管理',
            font=ctk.CTkFont(size=24, weight='bold')
        )
        title.pack(side='left')

    def _create_total_budget(self):
        total_status = self.budget_manager.get_total_budget_status(self.current_month)

        card = ctk.CTkFrame(self, corner_radius=10, fg_color='white')
        card.pack(fill='x', padx=20, pady=10)

        header_row = ctk.CTkFrame(card, fg_color='transparent')
        header_row.pack(fill='x', padx=20, pady=(20, 10))

        title_label = ctk.CTkLabel(header_row, text='总预算',
                                   font=ctk.CTkFont(size=16, weight='bold'))
        title_label.pack(side='left')

        edit_btn = ctk.CTkButton(header_row, text='设置', width=60,
                                  command=self._edit_total_budget)
        edit_btn.pack(side='right')

        amount_row = ctk.CTkFrame(card, fg_color='transparent')
        amount_row.pack(fill='x', padx=20, pady=5)

        budget_label = ctk.CTkLabel(amount_row,
                                    text=f'预算: ¥{total_status["budget"]:,.2f}',
                                    font=ctk.CTkFont(size=13))
        budget_label.pack(side='left')

        spent_label = ctk.CTkLabel(amount_row,
                                    text=f'已用: ¥{total_status["spent"]:,.2f}',
                                    font=ctk.CTkFont(size=13))
        spent_label.pack(side='right')

        progress_frame = ctk.CTkFrame(card, fg_color='transparent')
        progress_frame.pack(fill='x', padx=20, pady=10)

        progress_color = self._get_progress_color(total_status['status'])
        progress_pct = min(total_status['ratio'] * 100, 100)

        progress_bar = ctk.CTkProgressBar(progress_frame, height=20,
                                           progress_color=progress_color)
        progress_bar.set(progress_pct / 100)
        progress_bar.pack(fill='x')

        pct_label = ctk.CTkLabel(progress_frame,
                                  text=f'{progress_pct:.1f}%',
                                  font=ctk.CTkFont(size=12))
        pct_label.pack(pady=(5, 0))

        remaining_label = ctk.CTkLabel(card,
                                        text=f'剩余: ¥{total_status["remaining"]:,.2f}',
                                        font=ctk.CTkFont(size=13))
        remaining_label.pack(pady=(0, 20), padx=20, anchor='w')

    def _create_category_budgets(self):
        title_frame = ctk.CTkFrame(self, fg_color='transparent')
        title_frame.pack(fill='x', padx=20, pady=(20, 10))

        title_label = ctk.CTkLabel(title_frame, text='分类预算（含二级分类）',
                                   font=ctk.CTkFont(size=18, weight='bold'))
        title_label.pack(side='left')

        add_btn = ctk.CTkButton(title_frame, text='+ 添加分类预算', width=120,
                                 command=self._add_category_budget)
        add_btn.pack(side='right')

        tree = self.budget_manager.get_category_budget_status_tree(self.current_month)
        for parent in tree:
            self._create_parent_card(parent)

    def _create_parent_card(self, parent):
        card = ctk.CTkFrame(self, corner_radius=10, fg_color='white')
        card.pack(fill='x', padx=20, pady=5)

        content = ctk.CTkFrame(card, fg_color='transparent')
        content.pack(fill='x', padx=15, pady=12)

        icon_label = ctk.CTkLabel(content, text=parent['category_icon'],
                                   font=ctk.CTkFont(size=20))
        icon_label.pack(side='left')

        info_frame = ctk.CTkFrame(content, fg_color='transparent')
        info_frame.pack(side='left', fill='x', expand=True, padx=10)

        name_row = ctk.CTkFrame(info_frame, fg_color='transparent')
        name_row.pack(fill='x')

        name_label = ctk.CTkLabel(name_row, text=parent['category_name'],
                                   font=ctk.CTkFont(size=14, weight='bold'))
        name_label.pack(side='left')

        budget_text = f'¥{parent["budget"]:,.2f}' if parent['budget'] > 0 else '未设置'
        budget_label = ctk.CTkLabel(name_row, text=f'预算: {budget_text}',
                                     font=ctk.CTkFont(size=12), text_color='gray')
        budget_label.pack(side='right')

        progress_frame = ctk.CTkFrame(info_frame, fg_color='transparent')
        progress_frame.pack(fill='x', pady=(5, 0))

        if parent['budget'] > 0:
            progress_color = self._get_progress_color(parent['status'])
            progress_pct = min(parent['ratio'] * 100, 100)
            progress_bar = ctk.CTkProgressBar(progress_frame, height=12,
                                               progress_color=progress_color)
            progress_bar.set(progress_pct / 100)
            progress_bar.pack(fill='x')

            direct = parent.get('direct_spent', 0)
            spent_text = f'已用 ¥{parent["spent"]:,.2f} / ¥{parent["budget"]:,.2f} ({progress_pct:.1f}%)'
            if direct > 0:
                spent_text += f'  (直接支出 ¥{direct:,.2f})'
            spent_label = ctk.CTkLabel(progress_frame, text=spent_text,
                                        font=ctk.CTkFont(size=11), text_color='gray')
            spent_label.pack(pady=(3, 0), anchor='w')
        else:
            hint_label = ctk.CTkLabel(progress_frame, text='点击右侧按钮设置预算',
                                       font=ctk.CTkFont(size=11), text_color='gray')
            hint_label.pack(anchor='w')

        for child in parent.get('children', []):
            self._create_sub_row(progress_frame, child, parent['category_name'])

        btn = ctk.CTkButton(content, text='设置' if parent['budget'] == 0 else '编辑',
                             width=60, height=30,
                             command=lambda: self._edit_category_budget(
                                 parent['category_id'], parent['category_name']))
        btn.pack(side='right')

    def _create_sub_row(self, parent_frame, child, parent_name):
        sub_frame = ctk.CTkFrame(parent_frame, fg_color='#F8F9FA', corner_radius=6)
        sub_frame.pack(fill='x', pady=(5, 0))

        sub_content = ctk.CTkFrame(sub_frame, fg_color='transparent')
        sub_content.pack(fill='x', padx=10, pady=8)

        sub_name_row = ctk.CTkFrame(sub_content, fg_color='transparent')
        sub_name_row.pack(fill='x')

        sub_name = ctk.CTkLabel(
            sub_name_row,
            text=f"  └ {child['category_icon']} {child['category_name']}",
            font=ctk.CTkFont(size=12, weight='bold')
        )
        sub_name.pack(side='left')

        sub_budget_text = f'¥{child["budget"]:,.2f}' if child['budget'] > 0 else '未设置'
        sub_budget_label = ctk.CTkLabel(
            sub_name_row, text=f'预算: {sub_budget_text}',
            font=ctk.CTkFont(size=10), text_color='gray'
        )
        sub_budget_label.pack(side='right')

        if child['budget'] > 0:
            sub_progress_color = self._get_progress_color(child['status'])
            sub_progress_pct = min(child['ratio'] * 100, 100)
            sub_progress_bar = ctk.CTkProgressBar(sub_content, height=8,
                                                   progress_color=sub_progress_color)
            sub_progress_bar.set(sub_progress_pct / 100)
            sub_progress_bar.pack(fill='x', pady=(3, 0))

            sub_spent_label = ctk.CTkLabel(
                sub_content,
                text=f'已用 ¥{child["spent"]:,.2f} / ¥{child["budget"]:,.2f} ({sub_progress_pct:.1f}%)',
                font=ctk.CTkFont(size=10), text_color='gray'
            )
            sub_spent_label.pack(anchor='w', pady=(2, 0))

            edit_btn = ctk.CTkButton(
                sub_content, text='编辑', width=50, height=24,
                font=ctk.CTkFont(size=11),
                command=lambda: self._edit_category_budget(
                    child['category_id'], f'{parent_name} > {child["category_name"]}')
            )
            edit_btn.pack(side='right')

    def _create_warnings(self):
        warnings = self.budget_manager.get_warnings(self.current_month)
        if not warnings:
            return

        warning_frame = ctk.CTkFrame(self, corner_radius=10, fg_color='#FFF3CD')
        warning_frame.pack(fill='x', padx=20, pady=(20, 10))

        title = ctk.CTkLabel(warning_frame, text='⚠️ 预算预警',
                             font=ctk.CTkFont(size=14, weight='bold'),
                             text_color='#856404')
        title.pack(pady=(15, 10), padx=15, anchor='w')

        for w in warnings:
            color = '#8B0000' if w['level'] == 'danger' else '#856404'
            warn_label = ctk.CTkLabel(warning_frame, text=f'• {w["message"]}',
                                       text_color=color, font=ctk.CTkFont(size=12))
            warn_label.pack(anchor='w', padx=15, pady=2)

        ctk.CTkLabel(warning_frame, text='').pack(pady=5)

    def _get_progress_color(self, status):
        if status == 'danger':
            return '#FF6B6B'
        elif status == 'warning':
            return '#FFD93D'
        else:
            return '#4ECDC4'

    def _edit_total_budget(self):
        BudgetEditDialog(self, self.budget_manager, None,
                         f'{self.current_month} 总预算', self._on_budget_saved)

    def _edit_category_budget(self, category_id, category_name):
        BudgetEditDialog(self, self.budget_manager, category_id,
                         f'{self.current_month} {category_name} 预算', self._on_budget_saved)

    def _add_category_budget(self):
        CategoryBudgetSelectDialog(self, self.budget_manager, self.ledger,
                                    self._on_budget_saved)

    def _on_budget_saved(self):
        self.refresh_callback()


class BudgetEditDialog(ctk.CTkToplevel):
    def __init__(self, master, budget_manager, category_id, title, on_saved):
        super().__init__(master)
        self.budget_manager = budget_manager
        self.category_id = category_id
        self.on_saved = on_saved
        self.title(title)
        self.geometry('350x200')
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.current_month = self.budget_manager.get_current_month_str()

        frame = ctk.CTkFrame(self, fg_color='transparent')
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        label = ctk.CTkLabel(frame, text='预算金额 (元)', font=ctk.CTkFont(size=13))
        label.pack(anchor='w', pady=(10, 5))

        self.amount_var = ctk.StringVar()
        entry = ctk.CTkEntry(frame, textvariable=self.amount_var)
        entry.pack(fill='x')

        current = self.budget_manager.ds.get_budget(self.current_month, category_id)
        if current:
            self.amount_var.set(str(current['amount']))

        btn_frame = ctk.CTkFrame(frame, fg_color='transparent')
        btn_frame.pack(fill='x', pady=(30, 0))

        cancel_btn = ctk.CTkButton(btn_frame, text='取消', fg_color='gray',
                                    width=80, command=self.destroy)
        cancel_btn.pack(side='right')

        save_btn = ctk.CTkButton(btn_frame, text='保存', width=80,
                                  command=self._on_save)
        save_btn.pack(side='right', padx=10)

    def _on_save(self):
        try:
            amount = float(self.amount_var.get())
        except ValueError:
            messagebox.showerror('错误', '请输入有效的金额')
            return

        if amount < 0:
            messagebox.showerror('错误', '金额不能为负数')
            return

        try:
            if self.category_id:
                self.budget_manager.set_category_budget(self.current_month,
                                                         self.category_id, amount)
            else:
                self.budget_manager.set_total_budget(self.current_month, amount)
            self.on_saved()
            self.destroy()
        except Exception as e:
            messagebox.showerror('错误', str(e))


class CategoryBudgetSelectDialog(ctk.CTkToplevel):
    def __init__(self, master, budget_manager, ledger, on_saved):
        super().__init__(master)
        self.budget_manager = budget_manager
        self.ledger = ledger
        self.on_saved = on_saved
        self.title('选择分类')
        self.geometry('350x400')
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.expense_categories = ledger.get_categories('expense')
        self.current_month = self.budget_manager.get_current_month_str()
        existing_budgets = self.budget_manager.get_category_budgets(self.current_month)
        existing_ids = [b['category_id'] for b in existing_budgets if b['category_id']]

        frame = ctk.CTkFrame(self, fg_color='transparent')
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        label = ctk.CTkLabel(frame, text='选择要设置预算的分类',
                             font=ctk.CTkFont(size=14, weight='bold'))
        label.pack(pady=(0, 10), anchor='w')

        list_frame = ctk.CTkScrollableFrame(frame, fg_color='#F0F0F0')
        list_frame.pack(fill='both', expand=True)

        for cat in self.expense_categories:
            if cat['id'] in existing_ids:
                continue
            btn = ctk.CTkButton(list_frame,
                                 text=f"{cat['icon']} {cat['name']}",
                                 anchor='w',
                                 fg_color='white',
                                 text_color='black',
                                 hover_color='#E0E0E0',
                                 command=lambda cid=cat['id'], cname=cat['name']: self._on_select(cid, cname))
            btn.pack(fill='x', pady=3)

        cancel_btn = ctk.CTkButton(frame, text='取消', fg_color='gray',
                                    width=100, command=self.destroy)
        cancel_btn.pack(pady=(15, 0))

    def _on_select(self, category_id, category_name):
        self.destroy()
        BudgetEditDialog(self.master, self.budget_manager, category_id,
                         f'{self.current_month} {category_name} 预算',
                         self.on_saved)


class ReportPage(ctk.CTkScrollableFrame, Page):
    def __init__(self, master, report_generator=None, **kwargs):
        ctk.CTkScrollableFrame.__init__(self, master, corner_radius=0)
        Page.__init__(self, master, report_generator=report_generator, **kwargs)
        self.report_generator = report_generator
        self.current_month = datetime.now().strftime('%Y-%m')
        self.pack(fill='both', expand=True)

        self._create_header()
        self._create_bar_chart()
        self._create_category_summary()

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=20, pady=(20, 10))

        title = ctk.CTkLabel(
            header,
            text='📈 报表统计',
            font=ctk.CTkFont(size=24, weight='bold')
        )
        title.pack(side='left')

        export_summary_btn = ctk.CTkButton(
            header, text='📤 导出分类汇总',
            width=130, height=36,
            command=self._export_category_summary
        )
        export_summary_btn.pack(side='right', padx=(10, 0))

        export_txns_btn = ctk.CTkButton(
            header, text='📤 导出月度明细',
            width=130, height=36,
            fg_color='#45B7D1',
            command=self._export_monthly_transactions
        )
        export_txns_btn.pack(side='right')

        month_label = ctk.CTkLabel(header, text=f'当前月份: {self.current_month}',
                                    font=ctk.CTkFont(size=14), text_color='gray')
        month_label.pack(side='right', padx=(0, 20))

    def _export_monthly_transactions(self):
        default_name = f'{self.current_month}_交易明细.csv'
        file_path = filedialog.asksaveasfilename(
            title='导出月度交易明细',
            defaultextension='.csv',
            initialfile=default_name,
            filetypes=[('CSV 文件', '*.csv'), ('所有文件', '*.*')]
        )
        if not file_path:
            return
        try:
            self.report_generator.export_monthly_csv(self.current_month, file_path)
            messagebox.showinfo('导出成功', f'月度交易明细已导出到:\n{file_path}')
        except Exception as e:
            messagebox.showerror('导出失败', f'导出时出错: {e}')

    def _export_category_summary(self):
        default_name = f'{self.current_month}_分类汇总.csv'
        file_path = filedialog.asksaveasfilename(
            title='导出分类汇总',
            defaultextension='.csv',
            initialfile=default_name,
            filetypes=[('CSV 文件', '*.csv'), ('所有文件', '*.*')]
        )
        if not file_path:
            return
        try:
            self.report_generator.export_category_summary_csv(self.current_month, file_path)
            messagebox.showinfo('导出成功', f'分类汇总已导出到:\n{file_path}')
        except Exception as e:
            messagebox.showerror('导出失败', f'导出时出错: {e}')

    def _create_bar_chart(self):
        card = ctk.CTkFrame(self, corner_radius=10, fg_color='white')
        card.pack(fill='x', padx=20, pady=10)

        title = ctk.CTkLabel(card, text='📊 收支趋势',
                             font=ctk.CTkFont(size=16, weight='bold'))
        title.pack(pady=15, padx=15, anchor='w')

        chart_canvas = self.report_generator.create_income_expense_bar_chart(
            card, months=6, figsize=(7, 4))
        chart_canvas.get_tk_widget().pack(padx=15, pady=(0, 15))

    def _create_category_summary(self):
        summary = self.report_generator.create_category_summary_table_data(self.current_month)

        card = ctk.CTkFrame(self, corner_radius=10, fg_color='white')
        card.pack(fill='both', expand=True, padx=20, pady=(10, 20))

        title = ctk.CTkLabel(card, text='📋 分类收支汇总',
                             font=ctk.CTkFont(size=16, weight='bold'))
        title.pack(pady=15, padx=15, anchor='w')

        tables_frame = ctk.CTkFrame(card, fg_color='transparent')
        tables_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        income_frame = ctk.CTkFrame(tables_frame, corner_radius=8, fg_color='#E8F8F5')
        income_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        income_title = ctk.CTkLabel(income_frame, text='💰 收入分类',
                                     font=ctk.CTkFont(size=14, weight='bold'),
                                     text_color='#0D9488')
        income_title.pack(pady=10, anchor='center')

        income_tree = ttk.Treeview(income_frame, columns=('category', 'amount', 'pct'),
                                    show='headings', height=10)
        income_tree.heading('category', text='分类')
        income_tree.heading('amount', text='金额')
        income_tree.heading('pct', text='占比')
        income_tree.column('category', width=100, anchor='w')
        income_tree.column('amount', width=80, anchor='e')
        income_tree.column('pct', width=60, anchor='e')

        for item in summary['income_data']:
            income_tree.insert('', 'end',
                               values=(item['category'],
                                       f'¥{item["amount"]:,.2f}',
                                       f'{item["percentage"]:.1f}%'))

        income_tree.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        expense_frame = ctk.CTkFrame(tables_frame, corner_radius=8, fg_color='#FDF2F2')
        expense_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))

        expense_title = ctk.CTkLabel(expense_frame, text='💸 支出分类',
                                      font=ctk.CTkFont(size=14, weight='bold'),
                                      text_color='#E74C3C')
        expense_title.pack(pady=10, anchor='center')

        expense_tree = ttk.Treeview(expense_frame, columns=('category', 'amount', 'pct'),
                                     show='headings', height=10)
        expense_tree.heading('category', text='分类')
        expense_tree.heading('amount', text='金额')
        expense_tree.heading('pct', text='占比')
        expense_tree.column('category', width=100, anchor='w')
        expense_tree.column('amount', width=80, anchor='e')
        expense_tree.column('pct', width=60, anchor='e')

        for item in summary['expense_data']:
            expense_tree.insert('', 'end',
                                values=(item['category'],
                                        f'¥{item["amount"]:,.2f}',
                                        f'{item["percentage"]:.1f}%'))

        expense_tree.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        summary_row = ctk.CTkFrame(card, fg_color='transparent')
        summary_row.pack(fill='x', padx=15, pady=(0, 15))

        total_income_label = ctk.CTkLabel(summary_row,
                                           text=f'总收入: ¥{summary["total_income"]:,.2f}',
                                           font=ctk.CTkFont(size=13, weight='bold'),
                                           text_color='#0D9488')
        total_income_label.pack(side='left', padx=10)

        total_expense_label = ctk.CTkLabel(summary_row,
                                            text=f'总支出: ¥{summary["total_expense"]:,.2f}',
                                            font=ctk.CTkFont(size=13, weight='bold'),
                                            text_color='#E74C3C')
        total_expense_label.pack(side='left', padx=10)

        balance_label = ctk.CTkLabel(summary_row,
                                      text=f'结余: ¥{summary["balance"]:,.2f}',
                                      font=ctk.CTkFont(size=13, weight='bold'))
        balance_label.pack(side='right', padx=10)


class AccountsPage(ctk.CTkScrollableFrame, Page):
    def __init__(self, master, ledger=None, refresh_callback=None, **kwargs):
        ctk.CTkScrollableFrame.__init__(self, master, corner_radius=0)
        Page.__init__(self, master, ledger=ledger, refresh_callback=refresh_callback, **kwargs)
        self.ledger = ledger
        self.refresh_callback = refresh_callback
        self.pack(fill='both', expand=True)

        self._create_header()
        self._create_account_list()

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=20, pady=(20, 10))

        title = ctk.CTkLabel(header, text='💳 账户管理',
                             font=ctk.CTkFont(size=24, weight='bold'))
        title.pack(side='left')

        add_btn = ctk.CTkButton(header, text='+ 添加账户',
                                font=ctk.CTkFont(size=14), height=40,
                                command=self._open_add_dialog)
        add_btn.pack(side='right')

    def _create_account_list(self):
        accounts = self.ledger.get_account_balances()
        total_assets = sum(a['current_balance'] for a in accounts)

        total_frame = ctk.CTkFrame(self, corner_radius=10, fg_color='#45B7D1')
        total_frame.pack(fill='x', padx=20, pady=10)

        ctk.CTkLabel(total_frame, text='💰 总资产',
                     font=ctk.CTkFont(size=14), text_color='white').pack(
            side='left', padx=20, pady=15)
        ctk.CTkLabel(total_frame, text=f'¥{total_assets:,.2f}',
                     font=ctk.CTkFont(size=24, weight='bold'), text_color='white').pack(
            side='right', padx=20, pady=15)

        for acc in accounts:
            self._create_account_card(acc)

    def _create_account_card(self, acc):
        card = ctk.CTkFrame(self, corner_radius=10, fg_color='white')
        card.pack(fill='x', padx=20, pady=5)

        content = ctk.CTkFrame(card, fg_color='transparent')
        content.pack(fill='x', padx=15, pady=12)

        icon = ACCOUNT_TYPE_ICONS.get(acc['type'], '💰')
        type_label_text = ACCOUNT_TYPE_LABELS.get(acc['type'], acc['type'])

        icon_label = ctk.CTkLabel(content, text=icon, font=ctk.CTkFont(size=28))
        icon_label.pack(side='left', padx=(0, 15))

        info_frame = ctk.CTkFrame(content, fg_color='transparent')
        info_frame.pack(side='left', fill='x', expand=True)

        name_label = ctk.CTkLabel(info_frame, text=acc['name'],
                                   font=ctk.CTkFont(size=16, weight='bold'))
        name_label.pack(anchor='w')

        type_label = ctk.CTkLabel(info_frame, text=type_label_text,
                                   font=ctk.CTkFont(size=12), text_color='gray')
        type_label.pack(anchor='w')

        balance = acc['current_balance']
        color = '#4ECDC4' if balance >= 0 else '#FF6B6B'
        bal_label = ctk.CTkLabel(content, text=f'¥{balance:,.2f}',
                                 font=ctk.CTkFont(size=18, weight='bold'), text_color=color)
        bal_label.pack(side='right', padx=(10, 15))

        btn_frame = ctk.CTkFrame(content, fg_color='transparent')
        btn_frame.pack(side='right')

        ctk.CTkButton(btn_frame, text='编辑', width=60, height=30,
                      command=lambda: self._open_edit_dialog(acc['id'])).pack(side='left', padx=2)
        ctk.CTkButton(btn_frame, text='删除', width=60, height=30, fg_color='#FF6B6B',
                      command=lambda: self._delete_account(acc['id'])).pack(side='left', padx=2)

    def _open_add_dialog(self):
        AccountDialog(self, self.ledger, None, self._on_saved)

    def _open_edit_dialog(self, account_id):
        AccountDialog(self, self.ledger, account_id, self._on_saved)

    def _delete_account(self, account_id):
        if messagebox.askyesno('确认', '确定要删除此账户吗？删除后不可恢复。'):
            if self.ledger.delete_account(account_id):
                self._on_saved()
            else:
                messagebox.showerror('错误', '该账户仍有交易记录关联，无法删除。')

    def _on_saved(self):
        self.refresh_callback()


class AccountDialog(ctk.CTkToplevel):
    def __init__(self, master, ledger, account_id, on_saved):
        super().__init__(master)
        self.ledger = ledger
        self.account_id = account_id
        self.on_saved = on_saved
        self.title('编辑账户' if account_id else '添加账户')
        self.geometry('350x350')
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        frame = ctk.CTkFrame(self, fg_color='transparent')
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text='账户名称', font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(10, 5))
        self.name_var = ctk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.name_var, placeholder_text='如：招商银行卡').pack(fill='x')

        ctk.CTkLabel(frame, text='账户类型', font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
        self.type_var = ctk.StringVar(value='现金')
        type_values = list(ACCOUNT_TYPE_LABELS.values())
        ctk.CTkComboBox(frame, values=type_values, variable=self.type_var,
                        state='readonly').pack(fill='x')

        ctk.CTkLabel(frame, text='初始余额', font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
        self.balance_var = ctk.StringVar(value='0')
        ctk.CTkEntry(frame, textvariable=self.balance_var).pack(fill='x')

        btn_frame = ctk.CTkFrame(frame, fg_color='transparent')
        btn_frame.pack(fill='x', pady=(30, 0))
        ctk.CTkButton(btn_frame, text='取消', fg_color='gray', width=80,
                      command=self.destroy).pack(side='right')
        ctk.CTkButton(btn_frame, text='保存', width=80,
                      command=self._on_save).pack(side='right', padx=10)

        if account_id:
            self._load_account()

    def _load_account(self):
        acc = self.ledger.get_account(self.account_id)
        if acc:
            self.name_var.set(acc['name'])
            self.type_var.set(ACCOUNT_TYPE_LABELS.get(acc['type'], acc['type']))
            self.balance_var.set(str(acc['balance']))

    def _on_save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror('错误', '请输入账户名称')
            return

        type_reverse = {v: k for k, v in ACCOUNT_TYPE_LABELS.items()}
        type_ = type_reverse.get(self.type_var.get(), 'cash')

        try:
            balance = float(self.balance_var.get())
        except ValueError:
            messagebox.showerror('错误', '请输入有效的余额')
            return

        try:
            if self.account_id:
                self.ledger.update_account(self.account_id, name=name, type_=type_, balance=balance)
            else:
                self.ledger.add_account(name, type_, balance)
            self.on_saved()
            self.destroy()
        except Exception as e:
            messagebox.showerror('错误', str(e))


class RecurringRulesPage(ctk.CTkScrollableFrame, Page):
    def __init__(self, master, ledger=None, refresh_callback=None, **kwargs):
        ctk.CTkScrollableFrame.__init__(self, master, corner_radius=0)
        Page.__init__(self, master, ledger=ledger, refresh_callback=refresh_callback, **kwargs)
        self.ledger = ledger
        self.refresh_callback = refresh_callback
        self.pack(fill='both', expand=True)

        self._create_header()
        self._create_rules_list()

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=20, pady=(20, 10))

        title = ctk.CTkLabel(header, text='🔁 周期记账规则',
                             font=ctk.CTkFont(size=24, weight='bold'))
        title.pack(side='left')

        add_btn = ctk.CTkButton(header, text='+ 添加规则',
                                font=ctk.CTkFont(size=14), height=40,
                                command=self._open_add_dialog)
        add_btn.pack(side='right')

        process_btn = ctk.CTkButton(header, text='立即检查到期',
                                    font=ctk.CTkFont(size=14), height=40,
                                    fg_color='#4ECDC4',
                                    command=self._process_due)
        process_btn.pack(side='right', padx=(0, 10))

    def _create_rules_list(self):
        rules = self.ledger.get_recurring_rules()
        if not rules:
            empty = ctk.CTkFrame(self, corner_radius=10, fg_color='white')
            empty.pack(fill='x', padx=20, pady=20)
            ctk.CTkLabel(empty, text='暂无周期记账规则\n点击「添加规则」创建',
                         font=ctk.CTkFont(size=14), text_color='gray').pack(pady=40)
            return

        for rule in rules:
            self._create_rule_card(rule)

    def _create_rule_card(self, rule):
        card = ctk.CTkFrame(self, corner_radius=10, fg_color='white')
        card.pack(fill='x', padx=20, pady=5)

        content = ctk.CTkFrame(card, fg_color='transparent')
        content.pack(fill='x', padx=15, pady=12)

        status_color = '#4ECDC4' if rule['active'] else '#CCCCCC'
        status_dot = ctk.CTkLabel(content, text='●' if rule['active'] else '○',
                                  font=ctk.CTkFont(size=20), text_color=status_color)
        status_dot.pack(side='left', padx=(0, 10))

        info_frame = ctk.CTkFrame(content, fg_color='transparent')
        info_frame.pack(side='left', fill='x', expand=True)

        name_row = ctk.CTkFrame(info_frame, fg_color='transparent')
        name_row.pack(fill='x')

        name_label = ctk.CTkLabel(name_row, text=rule['name'] or '未命名规则',
                                   font=ctk.CTkFont(size=14, weight='bold'))
        name_label.pack(side='left')

        freq_label_text = FREQUENCY_LABELS.get(rule['frequency'], rule['frequency'])
        if rule['interval_val'] > 1:
            freq_label_text = f'每{rule["interval_val"]}{freq_label_text[1:]}'
        ctk.CTkLabel(name_row, text=freq_label_text,
                     font=ctk.CTkFont(size=12), text_color='gray').pack(side='right')

        detail_row = ctk.CTkFrame(info_frame, fg_color='transparent')
        detail_row.pack(fill='x', pady=(3, 0))

        type_text = {'income': '收入', 'expense': '支出', 'transfer': '转账'}.get(rule['type'], rule['type'])
        amount_text = f'¥{rule["amount"]:,.2f}'
        if rule['type'] == 'transfer':
            detail_text = f'转账 {rule.get("account_name", "?")}→{rule.get("to_account_name", "?")}  {amount_text}'
        elif rule['type'] == 'income':
            detail_text = f'{rule.get("category_icon", "")} {rule.get("category_name", "未分类")} +{amount_text}'
        else:
            detail_text = f'{rule.get("category_icon", "")} {rule.get("category_name", "未分类")} -{amount_text}'

        ctk.CTkLabel(detail_row, text=detail_text,
                     font=ctk.CTkFont(size=12), text_color='gray').pack(side='left')

        date_row = ctk.CTkFrame(info_frame, fg_color='transparent')
        date_row.pack(fill='x', pady=(3, 0))

        ctk.CTkLabel(date_row, text=f'下次执行: {rule["next_date"]}',
                     font=ctk.CTkFont(size=11), text_color='gray').pack(side='left')
        if rule.get('end_date'):
            ctk.CTkLabel(date_row, text=f'截止: {rule["end_date"]}',
                         font=ctk.CTkFont(size=11), text_color='gray').pack(side='right')

        btn_frame = ctk.CTkFrame(content, fg_color='transparent')
        btn_frame.pack(side='right')

        toggle_text = '停用' if rule['active'] else '启用'
        toggle_color = '#FFD93D' if rule['active'] else '#4ECDC4'
        ctk.CTkButton(btn_frame, text=toggle_text, width=50, height=28, fg_color=toggle_color,
                      font=ctk.CTkFont(size=11),
                      command=lambda rid=rule['id']: self._toggle_rule(rid)).pack(side='left', padx=2)
        ctk.CTkButton(btn_frame, text='删除', width=50, height=28, fg_color='#FF6B6B',
                      font=ctk.CTkFont(size=11),
                      command=lambda rid=rule['id']: self._delete_rule(rid)).pack(side='left', padx=2)

    def _process_due(self):
        generated = self.ledger.process_due_recurring()
        if generated > 0:
            messagebox.showinfo('周期记账', f'已生成 {generated} 笔到期的交易记录。')
            self.refresh_callback()
        else:
            messagebox.showinfo('周期记账', '当前没有到期的规则。')

    def _open_add_dialog(self):
        RecurringRuleDialog(self, self.ledger, None, self._on_saved)

    def _toggle_rule(self, rule_id):
        rule = self.ledger.get_recurring_rule(rule_id)
        if rule:
            self.ledger.update_recurring_rule(rule_id, active=0 if rule['active'] else 1)
            self._on_saved()

    def _delete_rule(self, rule_id):
        if messagebox.askyesno('确认', '确定要删除此周期记账规则吗？'):
            self.ledger.delete_recurring_rule(rule_id)
            self._on_saved()

    def _on_saved(self):
        self.refresh_callback()


class RecurringRuleDialog(ctk.CTkToplevel):
    def __init__(self, master, ledger, rule_id, on_saved):
        super().__init__(master)
        self.ledger = ledger
        self.rule_id = rule_id
        self.on_saved = on_saved
        self.title('编辑周期规则' if rule_id else '添加周期规则')
        self.geometry('420x640')
        self.resizable(False, True)
        self.transient(master)
        self.grab_set()

        self.categories = self.ledger.get_categories()
        self.accounts = self.ledger.get_accounts()

        self._create_widgets()

        if rule_id:
            self._load_rule()

    def _create_widgets(self):
        main_frame = ctk.CTkScrollableFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text='规则名称',
                     font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(10, 5))
        self.name_var = ctk.StringVar()
        ctk.CTkEntry(main_frame, textvariable=self.name_var,
                     placeholder_text='如：每月房租').pack(fill='x')

        ctk.CTkLabel(main_frame, text='类型',
                     font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
        type_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        type_frame.pack(fill='x')
        self.type_var = ctk.StringVar(value='expense')
        ctk.CTkRadioButton(type_frame, text='支出', variable=self.type_var,
                           value='expense', command=self._on_type_change).pack(side='left', padx=(0, 20))
        ctk.CTkRadioButton(type_frame, text='收入', variable=self.type_var,
                           value='income', command=self._on_type_change).pack(side='left', padx=(0, 20))
        ctk.CTkRadioButton(type_frame, text='转账', variable=self.type_var,
                           value='transfer', command=self._on_type_change).pack(side='left')

        ctk.CTkLabel(main_frame, text='金额',
                     font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
        self.amount_var = ctk.StringVar()
        ctk.CTkEntry(main_frame, textvariable=self.amount_var,
                     placeholder_text='请输入金额').pack(fill='x')

        self.detail_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        self.detail_frame.pack(fill='x')

        ctk.CTkLabel(main_frame, text='重复频率',
                     font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
        self.freq_var = ctk.StringVar(value='每月')
        ctk.CTkComboBox(main_frame, values=['每天', '每周', '每月', '每年'],
                        variable=self.freq_var, state='readonly', width=120).pack(anchor='w')

        ctk.CTkLabel(main_frame, text='间隔（每N个周期）',
                     font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
        self.interval_var = ctk.StringVar(value='1')
        ctk.CTkEntry(main_frame, textvariable=self.interval_var, width=80).pack(anchor='w')

        ctk.CTkLabel(main_frame, text='开始日期',
                     font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
        self.start_date_var = ctk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        ctk.CTkEntry(main_frame, textvariable=self.start_date_var).pack(fill='x')

        ctk.CTkLabel(main_frame, text='结束日期（可选）',
                     font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
        self.end_date_var = ctk.StringVar()
        ctk.CTkEntry(main_frame, textvariable=self.end_date_var,
                     placeholder_text='YYYY-MM-DD').pack(fill='x')
        ctk.CTkLabel(main_frame, text='留空表示无限重复',
                     font=ctk.CTkFont(size=11), text_color='gray').pack(anchor='w', pady=(2, 0))

        ctk.CTkLabel(main_frame, text='备注',
                     font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
        self.note_text = ctk.CTkTextbox(main_frame, height=60)
        self.note_text.pack(fill='x')

        btn_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        btn_frame.pack(fill='x', pady=(25, 10))
        ctk.CTkButton(btn_frame, text='取消', fg_color='gray', width=80,
                      command=self.destroy).pack(side='right')
        ctk.CTkButton(btn_frame, text='保存', width=80,
                      command=self._on_save).pack(side='right', padx=10)

        self._build_detail_section()

    def _build_detail_section(self):
        for widget in self.detail_frame.winfo_children():
            widget.destroy()

        type_ = self.type_var.get()
        account_names = [a['name'] for a in self.accounts]

        if type_ == 'transfer':
            ctk.CTkLabel(self.detail_frame, text='转出账户',
                         font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
            self.from_account_var = ctk.StringVar()
            ctk.CTkComboBox(self.detail_frame, values=account_names,
                           variable=self.from_account_var, state='readonly').pack(fill='x')
            if account_names:
                self.from_account_var.set(account_names[0])

            ctk.CTkLabel(self.detail_frame, text='转入账户',
                         font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
            self.to_account_var = ctk.StringVar()
            ctk.CTkComboBox(self.detail_frame, values=account_names,
                           variable=self.to_account_var, state='readonly').pack(fill='x')
            if len(account_names) > 1:
                self.to_account_var.set(account_names[1])
            elif account_names:
                self.to_account_var.set(account_names[0])
        else:
            ctk.CTkLabel(self.detail_frame, text='分类',
                         font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
            self.category_var = ctk.StringVar()
            self.category_combo = ctk.CTkComboBox(self.detail_frame, values=[],
                                                  variable=self.category_var, state='readonly')
            self.category_combo.pack(fill='x')
            self._refresh_categories()

            ctk.CTkLabel(self.detail_frame, text='账户',
                         font=ctk.CTkFont(size=13)).pack(anchor='w', pady=(15, 5))
            self.account_var = ctk.StringVar()
            ctk.CTkComboBox(self.detail_frame, values=account_names,
                           variable=self.account_var, state='readonly').pack(fill='x')
            if account_names:
                self.account_var.set(account_names[0])

    def _refresh_categories(self):
        if not hasattr(self, 'category_combo'):
            return
        type_ = self.type_var.get()
        cats = [c for c in self.categories if c['type'] == type_ and c.get('parent_id') is None]
        cat_display = [f"{c['icon']} {c['name']}" for c in cats]
        self.category_combo.configure(values=cat_display)
        if cat_display:
            self.category_var.set(cat_display[0])

    def _on_type_change(self):
        self._build_detail_section()

    def _get_account_id(self, name):
        for a in self.accounts:
            if a['name'] == name:
                return a['id']
        return None

    def _load_rule(self):
        rule = self.ledger.get_recurring_rule(self.rule_id)
        if not rule:
            return
        self.name_var.set(rule['name'])
        self.type_var.set(rule['type'])
        self._build_detail_section()
        self.amount_var.set(str(rule['amount']))

        freq_map = {'daily': '每天', 'weekly': '每周', 'monthly': '每月', 'yearly': '每年'}
        self.freq_var.set(freq_map.get(rule['frequency'], '每月'))
        self.interval_var.set(str(rule['interval_val']))
        self.start_date_var.set(rule['start_date'])
        if rule.get('end_date'):
            self.end_date_var.set(rule['end_date'])
        self.note_text.insert('1.0', rule.get('note') or '')

        if rule['type'] == 'transfer':
            for a in self.accounts:
                if a['id'] == rule['account_id']:
                    self.from_account_var.set(a['name'])
                if a['id'] == rule.get('to_account_id'):
                    self.to_account_var.set(a['name'])
        else:
            for c in self.categories:
                if c['id'] == rule.get('category_id'):
                    self.category_var.set(f"{c['icon']} {c['name']}")
                    break
            for a in self.accounts:
                if a['id'] == rule['account_id']:
                    self.account_var.set(a['name'])
                    break

    def _on_save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror('错误', '请输入规则名称')
            return

        try:
            amount = float(self.amount_var.get())
        except ValueError:
            messagebox.showerror('错误', '请输入有效的金额')
            return
        if amount <= 0:
            messagebox.showerror('错误', '金额必须大于0')
            return

        freq_map = {'每天': 'daily', '每周': 'weekly', '每月': 'monthly', '每年': 'yearly'}
        frequency = freq_map.get(self.freq_var.get(), 'monthly')
        try:
            interval_val = int(self.interval_var.get())
        except ValueError:
            messagebox.showerror('错误', '间隔必须为整数')
            return
        if interval_val < 1:
            messagebox.showerror('错误', '间隔必须大于0')
            return

        start_date = self.start_date_var.get()
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror('错误', '开始日期格式不正确')
            return

        end_date = self.end_date_var.get().strip()
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                messagebox.showerror('错误', '结束日期格式不正确')
                return

        type_ = self.type_var.get()
        note = self.note_text.get('1.0', 'end').strip()

        category_id = None
        account_id = None
        to_account_id = None

        if type_ == 'transfer':
            account_id = self._get_account_id(self.from_account_var.get())
            to_account_id = self._get_account_id(self.to_account_var.get())
            if not account_id or not to_account_id:
                messagebox.showerror('错误', '请选择转出和转入账户')
                return
            if account_id == to_account_id:
                messagebox.showerror('错误', '转出和转入账户不能相同')
                return
        else:
            cat_display = self.category_var.get()
            for c in self.categories:
                if f"{c['icon']} {c['name']}" == cat_display:
                    category_id = c['id']
                    break
            if not category_id:
                messagebox.showerror('错误', '请选择分类')
                return
            account_id = self._get_account_id(self.account_var.get())
            if not account_id:
                messagebox.showerror('错误', '请选择账户')
                return

        try:
            if self.rule_id:
                self.ledger.update_recurring_rule(
                    self.rule_id, name=name, frequency=frequency,
                    interval_val=interval_val, amount=amount, note=note, end_date=end_date or None
                )
            else:
                self.ledger.add_recurring_rule(
                    name, frequency, int(interval_val), type_, amount,
                    category_id, account_id, note, to_account_id=to_account_id,
                    start_date=start_date, end_date=end_date or None
                )
            self.on_saved()
            self.destroy()
        except Exception as e:
            messagebox.showerror('错误', str(e))


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
