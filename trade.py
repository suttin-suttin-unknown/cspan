import time

class Trade:
    def __init__(self, transactions):
        self.transactions = transactions

    def __dict__(self):
        return dict([])


def get_trade_volumes(transaction_range, token):
    long_volume, short_volume = 0, 0
    for (_, _, value) in transaction_range.get_token_trades(token):
        if value > 0:
            long_volume += value
        else:
            short_volume += value
    return long_volume, short_volume


def is_long_only(transaction_range, token):
    long_volume, short_volume = get_trade_volumes(transaction_range, token)
    return long_volume > 0 and short_volume == 0


def is_short_only(transaction_range, token):
    long_volume, short_volume = get_trade_volumes(transaction_range, token)
    return long_volume == 0 and short_volume < 0


def is_net_long(transaction_range, token):
    long_volume, short_volume = get_trade_volumes(transaction_range, token)
    return long_volume > abs(short_volume)


def is_net_short(transaction_range, token):
    long_volume, short_volume = get_trade_volumes(transaction_range, token)
    return long_volume < abs(short_volume)


def get_long_short_percentages(transaction_range, token):
    long_volume, short_volume = get_trade_volumes(transaction_range, token)
    total_volume = long_volume - short_volume
    long_perentage = long_volume / total_volume
    return long_perentage, 1 - long_perentage


def get_long_only_tokens(transaction_range):
    tokens = []
    for token in transaction_range.get_token_info().keys():
        if is_long_only(transaction_range, token):
            tokens.append(token)
    return tokens


def get_short_only_tokens(transaction_range):
    tokens = []
    for token in transaction_range.get_token_info().keys():
        if is_short_only(transaction_range, token):
            tokens.append(token)
    return tokens


def get_net_long_tokens(transaction_range):
    tokens = []
    for token in transaction_range.get_token_info().keys():
        if is_net_long(transaction_range, token):
            tokens.append(token)
    return tokens


def get_net_short_tokens(transaction_range):
    tokens = []
    for token in transaction_range.get_token_info().keys():
        if is_net_short(transaction_range, token):
            tokens.append(token)
    return tokens

