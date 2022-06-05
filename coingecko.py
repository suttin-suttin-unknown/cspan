import time

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

duplicate_mappings = {
    'uni': 'uniswap',
    'yfi': 'yearn-finance',
    'fxs': 'frax-share',
    'cvx': 'convex-finance',
    'bit': 'bitdao',
    'sand': 'the-sandbox',
    'spell': 'spell-token',
    'rbn': 'ribbon-finance',
    'ape': 'apecoin',
    'usdt': 'tether',
    'usdc': 'usd-coin',
    'wbtc': 'wrapped-bitcoin',
    'mana': 'decentraland',
    'link': 'chainlink',
    '1inch': '1inch',
    'sushi': 'sushi',
    'comp': 'compound-governance-token'
}


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


