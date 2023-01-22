import time
import operator

from pycoingecko import CoinGeckoAPI

def group_ids_by_symbol(coin_list):
    grouped = {}
    for entry in coin_list:
        if grouped.get(entry['symbol']):
            grouped[entry['symbol']].append(entry['id'])
        else:
            grouped[entry['symbol']] = [entry['id']]
    return grouped


api = CoinGeckoAPI()
main_list = group_ids_by_symbol(api.get_coins_list())

COINGECKO_CONTRACT_REGEX = '^0X[a-fA-F0-9]{40}$'


def get_coin_info(symbol):
    info = {}
    entries = main_list[symbol]
    for entry in entries:
        info[entry] = api.get_coin_by_id(entry)
    return info

def get_market_cap_fdv_ratio(coin_id):
    response = api.get_coin_by_id(coin_id)
    market_data = response['market_data']
    market_cap = market_data['market_cap']['usd']
    fdv = market_data['fully_diluted_valuation']['usd']
    return market_cap / fdv
    
def get_coin_market_data(coin_id, keys=['market_cap']):
    try:
        market_info = api.get_coin_by_id(coin_id)['market_data']
        market_info = [(k, market_info.get(k)) for k in keys]
        market_info = dict([(k, v) for k, v in market_info.items() if v])
    except:
        return None


def get_coin_id_for_symbol(symbol):
    symbol = symbol.lower()
    entry = main_list.get(symbol, [])
    if len(entry) == 0:
        return None
    elif len(entry) == 1:
        return entry[0]
    else:
        return duplicate_mappings[symbol]


def get_prices_for_range(coin_id, from_timestamp, to_timestamp=round(time.time())):
    from_timestamp = from_timestamp - (5 * 60)
    response = api.get_coin_market_chart_range_by_id(id=coin_id,
            vs_currency='usd', from_timestamp=from_timestamp, to_timestamp=to_timestamp)
    response = [(round(timestamp/1000), price) for timestamp, price in response['prices']]
    return response


def get_current_price(coin_id):
    response = api.get_price(ids=coin_id, vs_currencies='usd')
    return list(response.values())[0]['usd']


def get_inclusive_price_range(coin_id, from_timestamp, to_timestamp=round(time.time())):
    price_range = get_prices_for_range(coin_id, from_timestamp, to_timestamp)
    current_price = get_current_price(coin_id)
    price_range.append([round(time.time()), current_price])
    return dict(price_range)


def ticker_is_onchain(ticker):
    return re.match(COINGECKO_CONTRACT_REGEX, ticker['base']) or re.match(COINGECKO_CONTRACT_REGEX, ticker['target'])


class Coin:
    def __init__(self, coingecko_entry):
        self.coingecko_entry = coingecko_entry

    @classmethod
    def from_coingecko_id(cls, coingecko_id):
        try:
            return cls(api.get_coin_by_id(coingecko_id))
        except:
            raise

    @property
    def symbol(self):
        return self.coingecko_entry['symbol']

    @property
    def coingecko_id(self):
        return self.coingecko_entry['id']

    @property
    def tickers(self):
        return self.coingecko_entry['tickers']
     
    def refresh(self):
        self.coingecko_entry = api.get_coin_by_id(self.coingecko_id)

    @property
    def current_price(self):
        return self.coingecko_entry['market_data']['current_price']['usd']

    @property
    def market_cap_rank(self):
        return self.coingecko_entry['market_cap_rank']

    @property
    def twitter_name(self):
        return self.coingecko_entry['links']['twitter_screen_name']

    @property
    def mcap_fdv_ratio(self):
        market_data = self.coingecko_entry['market_data']
        return market_data['market_cap']['usd'] / market_data['fully_diluted_valuation']['usd']

    def sort_tickers_by(self, key):
        self.tickers.sort(key=operator.itemgetter(key))
        return self.tickers

    @property
    def exchange_centralization(self):
        results = []
        exchanges = set([t['market']['identifier'] for t in self.tickers])
        for e in exchanges:
            info = api.get_exchanges_by_id(e)
            results.append((e, info['centralized']))
        return results

    @property
    def exchange_spreads(self):
        spreads = []
        for ticker in self.tickers:
            try:
                market = ticker['market']['identifier']
                spread = float(ticker['bid_ask_spread_percentage'])
                spreads.append((market, spread))
            except TypeError:
                pass
        return spreads

    @property
    def min_spread_exchange(self):
        return sorted(self.exchange_spreads, key=lambda e: e[-1])[0]
    
    @property
    def max_spread_exchange(self):
        return sorted(self.exchange_spreads, key=lambda e: e[-1])[-1]

    @property
    def average_spread(self):
        return sum([es[-1] for es in self.exchange_spreads]) / len(self.exchange_spreads)

    @property
    def volume_weighted_average_spread(self):
        vwas = 0
        total_volumes = sum([t['volume'] for t in self.coingecko_entry['tickers']])
        for t in self.coingecko_entry['tickers']:
            weight = t['volume'] / total_volumes
            vwas += weight * t['bid_ask_spread_percentage']
        return vwas / len(self.exchange_spreads)

    @property
    def all_time_low_percentage(self):
        currencies = ['usd', 'btc', 'eth']
        changes = self.coingecko_entry['market_data']['atl_change_percentage']
        return dict(zip(currencies, operator.itemgetter(*currencies)(changes)))

    @property
    def all_time_high_percentage(self):
        currencies = ['usd', 'btc', 'eth']
        changes = self.coingecko_entry['market_data']['ath_change_percentage']
        return dict(zip(currencies, operator.itemgetter(*currencies)(changes)))

    @property
    def lowest_volume_exchange(self):
        ex = self.sort_tickers_by('volume')[0]
        return (ex['market']['identifier'], ex['volume'])

    @property
    def highest_volume_exchange(self):
        ex = self.sort_tickers_by('volume')[-1]
        return (ex['market']['identifier'], ex['volume'])

