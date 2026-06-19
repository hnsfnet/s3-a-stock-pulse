import os
from datastore import DataStore
from datetime import datetime, timedelta
import random


def add_sample_data():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ledger.db')

    if os.path.exists(db_path):
        os.remove(db_path)

    ds = DataStore()

    today = datetime.now()
    current_month = today.strftime('%Y-%m')

    cat_map = {}
    for c in ds.get_categories():
        cat_map[c['name']] = c['id']

    acc_map = {}
    for a in ds.get_accounts():
        acc_map[a['name']] = a['id']

    ds.update_account(acc_map['现金'], balance=2000)
    ds.update_account(acc_map['银行卡'], balance=15000)
    ds.update_account(acc_map['信用卡'], balance=-800)
    ds.update_account(acc_map['支付宝'], balance=3500)

    ds.add_transaction(
        f'{current_month}-05', 8500, 'income', cat_map['工资'], acc_map['银行卡'], '5月工资'
    )
    ds.add_transaction(
        f'{current_month}-10', 2000, 'income', cat_map['奖金'], acc_map['银行卡'], '项目奖金'
    )
    ds.add_transaction(
        f'{current_month}-15', 500, 'income', cat_map['投资收益'], acc_map['支付宝'], '理财收益'
    )

    sub_expense = [
        ('外卖', '餐饮'), ('堂食', '餐饮'), ('买菜', '餐饮'),
        ('地铁', '交通'), ('打车', '交通'),
        ('服饰', '购物'), ('日用', '购物'),
    ]
    parent_expense = ['娱乐', '医疗', '教育', '住房', '水电煤', '通讯']

    expense_pool = []
    for sub_name, parent_name in sub_expense:
        if sub_name in cat_map:
            expense_pool.append((cat_map[sub_name], sub_name))
    for pname in parent_expense:
        if pname in cat_map:
            expense_pool.append((cat_map[pname], pname))

    accounts = [acc_map['现金'], acc_map['银行卡'], acc_map['信用卡'], acc_map['支付宝']]

    for i in range(25):
        day = random.randint(1, min(today.day, 28))
        date_str = f'{current_month}-{day:02d}'

        cat_id, cat_name = random.choice(expense_pool)
        amount = round(random.uniform(20, 500), 2)
        account_id = random.choice(accounts)

        notes = ['', '日常消费', '周末聚餐', '通勤', '网购', '外卖']
        note = random.choice(notes)

        ds.add_transaction(date_str, amount, 'expense', cat_id, account_id, note)

    ds.add_transfer(
        f'{current_month}-01', 3000, acc_map['银行卡'], acc_map['支付宝'], '工资转支付宝'
    )
    ds.add_transfer(
        f'{current_month}-08', 1000, acc_map['支付宝'], acc_map['现金'], '提取现金'
    )

    last_month = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    for i in range(20):
        day = random.randint(1, 28)
        date_str = f'{last_month}-{day:02d}'

        cat_id, cat_name = random.choice(expense_pool)
        amount = round(random.uniform(30, 600), 2)
        account_id = random.choice(accounts)

        ds.add_transaction(date_str, amount, 'expense', cat_id, account_id, '')

    ds.add_transaction(
        f'{last_month}-05', 8500, 'income', cat_map['工资'], acc_map['银行卡'], '上月工资'
    )
    ds.add_transaction(
        f'{last_month}-20', 800, 'income', cat_map['投资收益'], acc_map['支付宝'], '股票分红'
    )
    ds.add_transfer(
        f'{last_month}-03', 2000, acc_map['银行卡'], acc_map['支付宝'], '转账'
    )

    for months_ago in range(2, 6):
        month_date = today.replace(day=1) - timedelta(days=months_ago * 31)
        month_str = month_date.strftime('%Y-%m')

        for i in range(random.randint(15, 22)):
            day = random.randint(1, 28)
            date_str = f'{month_str}-{day:02d}'

            cat_id, cat_name = random.choice(expense_pool)
            amount = round(random.uniform(25, 550), 2)
            account_id = random.choice(accounts)

            ds.add_transaction(date_str, amount, 'expense', cat_id, account_id, '')

        ds.add_transaction(
            f'{month_str}-05', 8500, 'income', cat_map['工资'], acc_map['银行卡'], ''
        )

    ds.add_recurring_rule(
        '每月工资', 'monthly', 1, 'income', 8500,
        cat_map['工资'], acc_map['银行卡'], '自动记账-工资',
        start_date=f'{current_month}-05'
    )
    ds.add_recurring_rule(
        '每月房租', 'monthly', 1, 'expense', 3500,
        cat_map['住房'], acc_map['银行卡'], '自动记账-房租',
        start_date=f'{current_month}-01'
    )
    ds.add_recurring_rule(
        '每月还信用卡', 'monthly', 1, 'transfer', 2000,
        None, acc_map['银行卡'], '自动还款',
        to_account_id=acc_map['信用卡'],
        start_date=f'{current_month}-10'
    )

    ds.set_budget(current_month, 8000, None)
    ds.set_budget(current_month, 2000, cat_map['餐饮'])
    ds.set_budget(current_month, 800, cat_map['外卖'])
    ds.set_budget(current_month, 500, cat_map['堂食'])
    ds.set_budget(current_month, 1000, cat_map['交通'])
    ds.set_budget(current_month, 1500, cat_map['购物'])
    ds.set_budget(current_month, 800, cat_map['娱乐'])
    ds.set_budget(current_month, 2000, cat_map['住房'])
    ds.set_budget(current_month, 300, cat_map['水电煤'])
    ds.set_budget(current_month, 200, cat_map['通讯'])

    summary = ds.get_monthly_summary(current_month)
    print('示例数据添加完成！')
    print(f'本月收入: ¥{summary["total_income"]:,.2f}')
    print(f'本月支出: ¥{summary["total_expense"]:,.2f}')
    print(f'本月结余: ¥{summary["balance"]:,.2f}')

    print('\n账户余额:')
    for acc in ds.get_account_balances():
        print(f'  {acc["name"]:6s} ¥{acc["current_balance"]:>10,.2f}')

    print('\n周期记账规则:')
    for rule in ds.get_recurring_rules():
        print(f'  {rule["name"]:12s} {rule["frequency"]:8s} ¥{rule["amount"]:>8,.2f}  下次: {rule["next_date"]}')

    txns = ds.get_transactions(limit=10)
    print(f'\n最近10笔交易:')
    for txn in txns:
        cat = txn.get('category_name') or '转账'
        print(f'  {txn["date"]} {txn["type"]:8s} {cat:8s} ¥{txn["amount"]:>8,.2f}')

    ds.close()


if __name__ == '__main__':
    add_sample_data()
