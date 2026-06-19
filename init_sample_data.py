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

    income_categories = [
        (1, '工资'),
        (2, '奖金'),
        (3, '投资收益'),
    ]

    expense_categories = [
        (5, '餐饮'),
        (6, '交通'),
        (7, '购物'),
        (8, '娱乐'),
        (9, '医疗'),
        (10, '教育'),
        (11, '住房'),
        (12, '水电煤'),
        (13, '通讯'),
    ]

    accounts = [1, 2, 3, 4]

    ds.add_transaction(
        f'{current_month}-05', 8500, 'income', 1, 2, '5月工资'
    )

    ds.add_transaction(
        f'{current_month}-10', 2000, 'income', 2, 2, '项目奖金'
    )

    ds.add_transaction(
        f'{current_month}-15', 500, 'income', 3, 2, '理财收益'
    )

    for i in range(25):
        day = random.randint(1, today.day)
        date_str = f'{current_month}-{day:02d}'

        cat_id, cat_name = random.choice(expense_categories)
        amount = round(random.uniform(20, 500), 2)
        account_id = random.choice(accounts)

        notes = ['', '日常消费', '周末聚餐', '通勤', '网购', '外卖']
        note = random.choice(notes)

        ds.add_transaction(date_str, amount, 'expense', cat_id, account_id, note)

    last_month = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    for i in range(20):
        day = random.randint(1, 28)
        date_str = f'{last_month}-{day:02d}'

        cat_id, cat_name = random.choice(expense_categories)
        amount = round(random.uniform(30, 600), 2)
        account_id = random.choice(accounts)

        ds.add_transaction(date_str, amount, 'expense', cat_id, account_id, '')

    ds.add_transaction(
        f'{last_month}-05', 8500, 'income', 1, 2, '上月工资'
    )
    ds.add_transaction(
        f'{last_month}-20', 800, 'income', 3, 2, '股票分红'
    )

    two_months_ago = (today.replace(day=1) - timedelta(days=32)).strftime('%Y-%m')
    for i in range(15):
        day = random.randint(1, 28)
        date_str = f'{two_months_ago}-{day:02d}'

        cat_id, cat_name = random.choice(expense_categories)
        amount = round(random.uniform(25, 400), 2)
        account_id = random.choice(accounts)

        ds.add_transaction(date_str, amount, 'expense', cat_id, account_id, '')

    ds.add_transaction(
        f'{two_months_ago}-05', 8500, 'income', 1, 2, ''
    )

    three_months_ago = (today.replace(day=1) - timedelta(days=63)).strftime('%Y-%m')
    for i in range(18):
        day = random.randint(1, 28)
        date_str = f'{three_months_ago}-{day:02d}'

        cat_id, cat_name = random.choice(expense_categories)
        amount = round(random.uniform(30, 450), 2)
        account_id = random.choice(accounts)

        ds.add_transaction(date_str, amount, 'expense', cat_id, account_id, '')

    ds.add_transaction(
        f'{three_months_ago}-05', 8500, 'income', 1, 2, ''
    )

    four_months_ago = (today.replace(day=1) - timedelta(days=94)).strftime('%Y-%m')
    for i in range(22):
        day = random.randint(1, 28)
        date_str = f'{four_months_ago}-{day:02d}'

        cat_id, cat_name = random.choice(expense_categories)
        amount = round(random.uniform(20, 550), 2)
        account_id = random.choice(accounts)

        ds.add_transaction(date_str, amount, 'expense', cat_id, account_id, '')

    ds.add_transaction(
        f'{four_months_ago}-05', 8500, 'income', 1, 2, ''
    )

    five_months_ago = (today.replace(day=1) - timedelta(days=125)).strftime('%Y-%m')
    for i in range(20):
        day = random.randint(1, 28)
        date_str = f'{five_months_ago}-{day:02d}'

        cat_id, cat_name = random.choice(expense_categories)
        amount = round(random.uniform(25, 500), 2)
        account_id = random.choice(accounts)

        ds.add_transaction(date_str, amount, 'expense', cat_id, account_id, '')

    ds.add_transaction(
        f'{five_months_ago}-05', 8500, 'income', 1, 2, ''
    )

    ds.set_budget(current_month, 8000, None)
    ds.set_budget(current_month, 2000, 5)
    ds.set_budget(current_month, 1000, 6)
    ds.set_budget(current_month, 1500, 7)
    ds.set_budget(current_month, 800, 8)
    ds.set_budget(current_month, 2000, 11)
    ds.set_budget(current_month, 300, 12)
    ds.set_budget(current_month, 200, 13)

    summary = ds.get_monthly_summary(current_month)
    print(f'示例数据添加完成！')
    print(f'本月收入: ¥{summary["total_income"]:,.2f}')
    print(f'本月支出: ¥{summary["total_expense"]:,.2f}')
    print(f'本月结余: ¥{summary["balance"]:,.2f}')

    txns = ds.get_transactions(limit=10)
    print(f'\n最近10笔交易:')
    for txn in txns:
        print(f'  {txn["date"]} {txn["type"]:6s} {txn["category_name"]:6s} ¥{txn["amount"]:>8,.2f}')

    ds.close()


if __name__ == '__main__':
    add_sample_data()
