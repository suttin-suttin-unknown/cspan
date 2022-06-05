from transactions import *
from coingecko import *

alabama = get_alias_address('Alameda 1 (allegedly)', 'all_wallets.txt')
r = TransactionRange(alabama, start_block=get_timestamp_for_range(TransactionRangeOptions.WEEK_START))
