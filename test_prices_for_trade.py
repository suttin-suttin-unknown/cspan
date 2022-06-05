import pprint
from transactions import *

alabama = get_alias_address('Alameda 1 (allegedly)', 'all_wallets.txt')
print(alabama)

tr = TransactionRange(alabama, start_block=get_timestamp_for_range(TransactionRangeOptions.WEEK_START))

matic_trades = tr.get_trades('MATIC')
prices = get_prices_for_range('matic-network', from_timestamp=matic_trades[0][0])
current_price = get_latest_price('matic-network')
prices.append(current_price)

price_dict = dict([(price_ts, price) for [price_ts, price] in prices])
series = sorted(list(price_dict.keys()))

priced_trades = []

for trade in matic_trades:
    for n in range(len(series) - 1):
        trade_time = trade[0]
        time_l = series[n]
        time_r = series[n + 1]
        if time_l <= trade_time <= time_r:
            left_diff = trade_time - time_l
            right_diff = time_r - trade_time
            price = price_dict[time_l] if left_diff < right_diff else price_dict[time_r]
            trade = trade + (price,)
            print(f"Left price: {price_dict[time_l]} Right price: {price_dict[time_r]}")
            print(f"Time: {trade_time}, Left: {left_diff}, Right: {right_diff}, Price: {price}")
            pprint.pprint(trade)
            break



