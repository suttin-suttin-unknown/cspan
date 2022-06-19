import time

from transactions import Transactions, TransactionRange, get_alias_address
from datetime import datetime
from coingecko import *


def format_trade(trade):
    date = datetime.fromtimestamp(trade[0][0])
    if len(trade) > 1:
        [l, r] = trade
        l, r = [str(_) for _ in l[1:]], [str(_) for _ in r[1:]]
        l, r = " ".join(reversed(l)), " ".join(reversed(r))
        return f"{date}: {l}: {r}"
    else:
        trade = " ".join(reversed([str(_) for _ in trade[0][1:]]))
        return "{}: {}".format(date, trade)


def watch(address, interval=120): 
    start_block = round(time.time())
    try:
        while True:
            print("Sleeping\n")
            time.sleep(interval)
            latest = TransactionRange(address, start_block=start_block)
            print(len(latest))
            if len(latest) > 0:
                start_block = latest.end_block
                table = latest.get_trade_table()
                for h in table:
                    print(format_trade(table[h]))
                print(latest.get_balance_changes(latest.token_list))
            else:
                print("No New transactions. Sleeping.\n")
                start_block = round(time.time())
    except KeyboardInterrupt:
        print("Stopping.")

alabama = get_alias_address('Alameda 1 (allegedly)', 'all_wallets.txt')
