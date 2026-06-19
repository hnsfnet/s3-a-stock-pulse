import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime, date
from datastore import DataStore
from ledger import Ledger
from budget_manager import BudgetManager
from report_generator import ReportGenerator

ctk.set_appearance_mode('light')
ctk.set_default_color_theme('blue')


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('个人记账本')
        self.geometry('1000x700')
        self.minsize(900, 600)

        self.ds = DataStore()
        self.ledger = Ledger(self.ds)
        self.budget_manager = BudgetManager(self.ds)
        self.report_generator = ReportGenerator(self.ds)

        self.current_page = 'overview'
        self.current_month = self.ledger.get_current_month_str()

        self._create_sidebar()
        self._create_main_area()
        self._show_overview_page()

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

        self.btn_overview = self._create_sidebar_button('📊 概览', self._show_overview_page)
        self.btn_transactions = self._create_sidebar_button('📝 交易明细', self._show_transactions_page)
        self.btn_budget = self._create_sidebar_button('🎯 预算管理', self._show_budget_page)
        self.btn_report = self._create_sidebar_button('📈 报表统计', self._show_report_page)

        self.btn_overview.pack(pady=5, padx=10, fill='x')
        self.btn_transactions.pack(pady=5, padx=10, fill='x')
        self.btn_budget.pack(pady=5, padx=10, fill='x')
        self.btn_report.pack(pady=5, padx=10, fill='x')

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

    def _update_sidebar_active(self, active_btn):
        for btn in [self.btn_overview, self.btn_transactions, self.btn_budget, self.btn_report]:
            btn.configure(fg_color='transparent', text_color=('gray10', 'gray90'))
        active_btn.configure(fg_color=('#3B8ED0', '#1F6AA5'), text_color='white')

    def _create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.pack(side='right', fill='both', expand=True)
        self.main_frame.pack_propagate(False)

    def _clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def _show_overview_page(self):
        self.current_page = 'overview'
        self._update_sidebar_active(self.btn_overview)
        self._clear_main_frame()
        OverviewPage(self.main_frame, self.ledger, self.budget_manager, self.report_generator)

    def _show_transactions_page(self):
        self.current_page = 'transactions'
        self._update_sidebar_active(self.btn_transactions)
        self._clear_main_frame()
        TransactionsPage(self.main_frame, self.ledger, self._refresh_all)

    def _show_budget_page(self):
        self.current_page = 'budget'
        self._update_sidebar_active(self.btn_budget)
        self._clear_main_frame()
        BudgetPage(self.main_frame, self.budget_manager, self.ledger, self._refresh_all)

    def _show_report_page(self):
        self.current_page = 'report'
        self._update_sidebar_active(self.btn_report)
        self._clear_main_frame()
        ReportPage(self.main_frame, self.report_generator)

    def _refresh_all(self):
        if self.current_page == 'overview':
            self._show_overview_page()
        elif self.current_page == 'transactions':
            self._show_transactions_page()
        elif self.current_page == 'budget':
            self._show_budget_page()
        elif self.current_page == 'report':
            self._show_report_page()

    def destroy(self):
        self.ds.close()
        super().destroy()


class OverviewPage(ctk.CTkScrollableFrame):
    def __init__(self, master, ledger, budget_manager, report_generator):
        super().__init__(master, corner_radius=0)
        self.ledger = ledger
        self.budget_manager = budget_manager
        self.report_generator = report_generator
        self.current_month = self.ledger.get_current_month_str()
        self.pack(fill='both', expand=True)

        self._create_header()
        self._create_summary_cards()
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

        icon_bg = '#E8F8F5' if txn['type'] == 'income' else '#FDF2F2'
        icon_color = '#4ECDC4' if txn['type'] == 'income' else '#FF6B6B'
        amount_prefix = '+' if txn['type'] == 'income' else '-'

        icon_frame = ctk.CTkFrame(item, width=40, height=40, corner_radius=20,
                                  fg_color=icon_bg)
        icon_frame.pack(side='left')
        icon_frame.pack_propagate(False)

        icon_label = ctk.CTkLabel(icon_frame, text=txn['category_icon'],
                                  font=ctk.CTkFont(size=18))
        icon_label.pack(expand=True)

        info_frame = ctk.CTkFrame(item, fg_color='transparent')
        info_frame.pack(side='left', fill='x', expand=True, padx=10)

        top_row = ctk.CTkFrame(info_frame, fg_color='transparent')
        top_row.pack(fill='x')

        category_label = ctk.CTkLabel(top_row, text=txn['category_name'],
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


class TransactionsPage(ctk.CTkFrame):
    def __init__(self, master, ledger, refresh_callback):
        super().__init__(master, corner_radius=0, fg_color='transparent')
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
        type_combo = ctk.CTkComboBox(filter_frame, values=['全部', '收入', '支出'],
                                     variable=self.type_var, width=80,
                                     command=lambda e: self._on_filter_change())
        type_combo.pack(side='left', padx=5, pady=15)

        cat_label = ctk.CTkLabel(filter_frame, text='分类:')
        cat_label.pack(side='left', padx=(10, 5), pady=15)

        self.category_var = ctk.StringVar(value='全部分类')
        categories = self.ledger.get_categories()
        cat_values = ['全部分类'] + [c['name'] for c in categories]
        self.category_combo = ctk.CTkComboBox(filter_frame, values=cat_values,
                                              variable=self.category_var, width=100,
                                              command=lambda e: self._on_filter_change())
        self.category_combo.pack(side='left', padx=5, pady=15)

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

        type_ = None
        if self.type_var.get() == '收入':
            type_ = 'income'
        elif self.type_var.get() == '支出':
            type_ = 'expense'

        category_id = None
        cat_name = self.category_var.get()
        if cat_name != '全部分类':
            categories = self.ledger.get_categories()
            for c in categories:
                if c['name'] == cat_name:
                    category_id = c['id']
                    break

        keyword = self.search_var.get() if self.search_var.get() else None
        start_date = self.date_start_var.get() if self.date_start_var.get() else None
        end_date = self.date_end_var.get() if self.date_end_var.get() else None

        transactions = self.ledger.list_transactions(
            start_date=start_date,
            end_date=end_date,
            type_=type_,
            category_id=category_id,
            keyword=keyword
        )

        for txn in transactions:
            type_text = '收入' if txn['type'] == 'income' else '支出'
            amount_text = f'+¥{txn["amount"]:,.2f}' if txn['type'] == 'income' else f'-¥{txn["amount"]:,.2f}'
            category_text = f"{txn['category_icon']} {txn['category_name']}"
            self.tree.insert('', 'end', iid=str(txn['id']),
                             values=(txn['date'], type_text, category_text,
                                     txn['account_name'], amount_text, txn['note'], '编辑/删除'))

    def _on_row_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            txn_id = int(item)
            self._open_edit_dialog(txn_id)

    def _open_add_dialog(self):
        TransactionDialog(self, self.ledger, None, self._on_transaction_saved)

    def _open_edit_dialog(self, txn_id):
        TransactionDialog(self, self.ledger, txn_id, self._on_transaction_saved)

    def _on_transaction_saved(self):
        self._refresh_list()
        self.refresh_callback()


class TransactionDialog(ctk.CTkToplevel):
    def __init__(self, master, ledger, txn_id, on_saved):
        super().__init__(master)
        self.ledger = ledger
        self.txn_id = txn_id
        self.on_saved = on_saved
        self.title('编辑交易' if txn_id else '新增交易')
        self.geometry('400x500')
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.categories = self.ledger.get_categories()
        self.accounts = self.ledger.get_accounts()

        self._create_widgets()

        if txn_id:
            self._load_transaction()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        type_label = ctk.CTkLabel(main_frame, text='类型', font=ctk.CTkFont(size=13))
        type_label.pack(anchor='w', pady=(10, 5))

        type_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        type_frame.pack(fill='x')

        self.type_var = ctk.StringVar(value='expense')
        expense_btn = ctk.CTkRadioButton(type_frame, text='支出', variable=self.type_var,
                                          value='expense', command=self._on_type_change)
        expense_btn.pack(side='left', padx=(0, 20))

        income_btn = ctk.CTkRadioButton(type_frame, text='收入', variable=self.type_var,
                                         value='income', command=self._on_type_change)
        income_btn.pack(side='left')

        date_label = ctk.CTkLabel(main_frame, text='日期', font=ctk.CTkFont(size=13))
        date_label.pack(anchor='w', pady=(15, 5))

        self.date_var = ctk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        date_entry = ctk.CTkEntry(main_frame, textvariable=self.date_var)
        date_entry.pack(fill='x')

        amount_label = ctk.CTkLabel(main_frame, text='金额', font=ctk.CTkFont(size=13))
        amount_label.pack(anchor='w', pady=(15, 5))

        self.amount_var = ctk.StringVar()
        amount_entry = ctk.CTkEntry(main_frame, textvariable=self.amount_var,
                                     placeholder_text='请输入金额')
        amount_entry.pack(fill='x')

        category_label = ctk.CTkLabel(main_frame, text='分类', font=ctk.CTkFont(size=13))
        category_label.pack(anchor='w', pady=(15, 5))

        self.category_var = ctk.StringVar()
        self.category_combo = ctk.CTkComboBox(main_frame, values=[],
                                               variable=self.category_var, state='readonly')
        self.category_combo.pack(fill='x')
        self._refresh_categories()

        account_label = ctk.CTkLabel(main_frame, text='账户', font=ctk.CTkFont(size=13))
        account_label.pack(anchor='w', pady=(15, 5))

        self.account_var = ctk.StringVar()
        account_names = [a['name'] for a in self.accounts]
        self.account_combo = ctk.CTkComboBox(main_frame, values=account_names,
                                              variable=self.account_var, state='readonly')
        self.account_combo.pack(fill='x')
        if account_names:
            self.account_var.set(account_names[0])

        note_label = ctk.CTkLabel(main_frame, text='备注', font=ctk.CTkFont(size=13))
        note_label.pack(anchor='w', pady=(15, 5))

        self.note_text = ctk.CTkTextbox(main_frame, height=80)
        self.note_text.pack(fill='x')

        btn_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        btn_frame.pack(fill='x', pady=(25, 0))

        if self.txn_id:
            delete_btn = ctk.CTkButton(btn_frame, text='删除', fg_color='#FF6B6B',
                                        width=80, command=self._on_delete)
            delete_btn.pack(side='left')

        cancel_btn = ctk.CTkButton(btn_frame, text='取消', fg_color='gray',
                                    width=80, command=self.destroy)
        cancel_btn.pack(side='right')

        save_btn = ctk.CTkButton(btn_frame, text='保存', width=80,
                                  command=self._on_save)
        save_btn.pack(side='right', padx=10)

    def _refresh_categories(self):
        type_ = self.type_var.get()
        cats = [c for c in self.categories if c['type'] == type_]
        cat_display = [f"{c['icon']} {c['name']}" for c in cats]
        self.category_combo.configure(values=cat_display)
        if cat_display:
            self.category_var.set(cat_display[0])

    def _on_type_change(self):
        self._refresh_categories()

    def _load_transaction(self):
        txn = self.ledger.get_transaction(self.txn_id)
        if txn:
            self.type_var.set(txn['type'])
            self._refresh_categories()
            self.date_var.set(txn['date'])
            self.amount_var.set(str(txn['amount']))

            category_display = f"{txn['category_icon']} {txn['category_name']}"
            self.category_var.set(category_display)

            self.account_var.set(txn['account_name'])
            self.note_text.insert('1.0', txn['note'])

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
        cat_display = self.category_var.get()

        category_id = None
        for c in self.categories:
            if f"{c['icon']} {c['name']}" == cat_display:
                category_id = c['id']
                break

        if category_id is None:
            messagebox.showerror('错误', '请选择分类')
            return

        account_id = None
        for a in self.accounts:
            if a['name'] == self.account_var.get():
                account_id = a['id']
                break

        if account_id is None:
            messagebox.showerror('错误', '请选择账户')
            return

        note = self.note_text.get('1.0', 'end').strip()

        try:
            if self.txn_id:
                self.ledger.update_transaction(
                    self.txn_id, date_str, amount, type_, category_id, account_id, note
                )
            else:
                self.ledger.add_transaction(
                    date_str, amount, type_, category_id, account_id, note
                )

            self.on_saved()
            self.destroy()
        except Exception as e:
            messagebox.showerror('错误', str(e))

    def _on_delete(self):
        if messagebox.askyesno('确认', '确定要删除这条交易记录吗？'):
            if self.ledger.delete_transaction(self.txn_id):
                self.on_saved()
                self.destroy()


class BudgetPage(ctk.CTkScrollableFrame):
    def __init__(self, master, budget_manager, ledger, refresh_callback):
        super().__init__(master, corner_radius=0)
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

        title_label = ctk.CTkLabel(title_frame, text='分类预算',
                                   font=ctk.CTkFont(size=18, weight='bold'))
        title_label.pack(side='left')

        add_btn = ctk.CTkButton(title_frame, text='+ 添加分类预算', width=120,
                                 command=self._add_category_budget)
        add_btn.pack(side='right')

        category_statuses = self.budget_manager.get_category_budget_status(self.current_month)
        expense_cats = self.ledger.get_categories('expense')

        budget_cat_ids = [cs['category_id'] for cs in category_statuses]
        for cat in expense_cats:
            if cat['id'] not in budget_cat_ids:
                category_statuses.append({
                    'category_id': cat['id'],
                    'category_name': cat['name'],
                    'category_icon': cat['icon'],
                    'budget': 0,
                    'spent': 0,
                    'remaining': 0,
                    'ratio': 0,
                    'status': 'normal'
                })

        for cs in category_statuses:
            self._create_category_budget_card(cs)

    def _create_category_budget_card(self, cs):
        card = ctk.CTkFrame(self, corner_radius=10, fg_color='white')
        card.pack(fill='x', padx=20, pady=5)

        content = ctk.CTkFrame(card, fg_color='transparent')
        content.pack(fill='x', padx=15, pady=12)

        icon_label = ctk.CTkLabel(content, text=cs['category_icon'],
                                   font=ctk.CTkFont(size=20))
        icon_label.pack(side='left')

        info_frame = ctk.CTkFrame(content, fg_color='transparent')
        info_frame.pack(side='left', fill='x', expand=True, padx=10)

        name_row = ctk.CTkFrame(info_frame, fg_color='transparent')
        name_row.pack(fill='x')

        name_label = ctk.CTkLabel(name_row, text=cs['category_name'],
                                   font=ctk.CTkFont(size=14, weight='bold'))
        name_label.pack(side='left')

        if cs['budget'] > 0:
            budget_text = f'¥{cs["budget"]:,.2f}'
        else:
            budget_text = '未设置'
        budget_label = ctk.CTkLabel(name_row, text=f'预算: {budget_text}',
                                     font=ctk.CTkFont(size=12), text_color='gray')
        budget_label.pack(side='right')

        progress_frame = ctk.CTkFrame(info_frame, fg_color='transparent')
        progress_frame.pack(fill='x', pady=(5, 0))

        if cs['budget'] > 0:
            progress_color = self._get_progress_color(cs['status'])
            progress_pct = min(cs['ratio'] * 100, 100)
            progress_bar = ctk.CTkProgressBar(progress_frame, height=10,
                                               progress_color=progress_color)
            progress_bar.set(progress_pct / 100)
            progress_bar.pack(fill='x')

            spent_label = ctk.CTkLabel(progress_frame,
                                        text=f'已用 ¥{cs["spent"]:,.2f} / ¥{cs["budget"]:,.2f} ({progress_pct:.1f}%)',
                                        font=ctk.CTkFont(size=11), text_color='gray')
            spent_label.pack(pady=(3, 0), anchor='w')
        else:
            hint_label = ctk.CTkLabel(progress_frame, text='点击右侧按钮设置预算',
                                       font=ctk.CTkFont(size=11), text_color='gray')
            hint_label.pack(anchor='w')

        btn = ctk.CTkButton(content, text='设置' if cs['budget'] == 0 else '编辑',
                             width=60, height=30,
                             command=lambda: self._edit_category_budget(cs['category_id'], cs['category_name']))
        btn.pack(side='right')

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


class ReportPage(ctk.CTkScrollableFrame):
    def __init__(self, master, report_generator):
        super().__init__(master, corner_radius=0)
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

        month_label = ctk.CTkLabel(header, text=f'当前月份: {self.current_month}',
                                    font=ctk.CTkFont(size=14), text_color='gray')
        month_label.pack(side='right')

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


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
