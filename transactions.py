import time
import pprint
import math
from operator import itemgetter
from datetime import datetime, timedelta
from json import JSONDecodeError

from config import get_etherscan_api_key
from etherscan import Etherscan

from options import *

etherscan_api_key = get_etherscan_api_key()
etherscan_api = Etherscan(etherscan_api_key)


def get_alias_address(alias, path):
    with open(path, 'r') as f:
        for line in f.readlines():
            try:
                _alias, address = line.split(',')
                if alias == _alias:
                    return address.strip()
            except ValueError:
                continue


def get_timestamp_block_number(timestamp):
    return etherscan_api.get_block_number_by_timestamp(timestamp=timestamp, closest='before')


def convert_token_value(value, decimal):
    return int(value) * pow(10, -1 * int(decimal))


def get_address_token_balance(contract_address, wallet_address):
    return int(etherscan_api.get_acc_balance_by_token_and_contract_address(contract_address=contract_address,
        address=wallet_address))


def get_address_transactions(address, start, end):
    try:
        print(f"Start: {start}, End: {end}")
        startblock = get_timestamp_block_number(start)
        endblock = get_timestamp_block_number(end)
        all_transactions = []
        finished = False

        while not finished:
            transactions = etherscan_api.get_erc20_token_transfer_events_by_address(address=address,
                startblock=startblock, endblock=endblock, sort='asc')
            all_transactions += transactions
            lastblock = transactions[-1]['blockNumber']
            if len(transactions) != 10000:
                finished = True
            else:
                startblock = lastblock

        return all_transactions
    except AssertionError:
        return []



def get_trade_from_transaction(transaction, wallet_address):
    try:
        symbol = transaction['tokenSymbol']
        timestamp = int(transaction['timeStamp'])
        value = transaction['value']
        value = convert_token_value(value, transaction['tokenDecimal'])
        value_sign = -1 if wallet_address == transaction['from'] else 1
        value *= value_sign
        return timestamp, symbol, value
    except KeyError:
        print(f"Malformed transaction: {transaction}")


class TransactionRange:

    def __init__(self, address, start_block=None, end_block=None):
        if not start_block:
            start_block = get_timestamp_for_range(TransactionRangeOptions.DAY)

        if not end_block:
            end_block = round(time.time())

        self.address = address
        self.start_block = start_block
        self.end_block = end_block
        self._transactions = get_address_transactions(address, start_block, end_block)
        self._timestamp = datetime.fromtimestamp(round(time.time()))


    def __len__(self):
        return len(self._transactions)


    @property
    def token_list(self):
        return list(self.get_info().keys())


    def get_info(self):
        info = {}
        for tx in self._transactions:
            symbol = tx['tokenSymbol']
            if not info.get(symbol):
                info[symbol] = dict((k, v) for k, v in tx.items()
                    if k in ['tokenName', 'tokenDecimal', 'contractAddress'])
        return info


    def get_balance(self, token):
        balance = get_address_token_balance(self.get_info()[token]['contractAddress'], self.address)
        balance = convert_token_value(balance, self.get_info()[token]['tokenDecimal']) 
        return balance


    def get_transactions_for_token(self, token):
        return filter(lambda t: t['tokenSymbol'] == token, self._transactions)


# Possibly create new trades object

    def get_trades(self, token, include_hash=False):
        trades = []
        for tx in filter(lambda tx: tx['tokenSymbol'] == token, self._transactions):
            trade = get_trade_from_transaction(tx, self.address)
            if include_hash:
                trades.append((tx['hash'], trade))
            else:
                trades.append(trade)
        return trades


    def get_volume(self, token):
        return sum([volume for _, _, volume in self.get_trades(token)])


    def get_balance_change(self, token):
        try:
            balance = self.get_balance(token)
            volume = self.get_volume(token)
            if volume >= 0:
                change =  volume / (balance - volume)
            else:
                change = volume / balance
        except ZeroDivisionError:
            return float('inf') if volume >= 0 else float('-inf')

        return change * 100

    
    def get_balance_changes(self, tokens):
        changes = {}
        for token in tokens:
            changes[token] = self.get_balance_change(token)
        return changes


    def get_volumes(self):
        volumes = {}
        for token in self.token_list:
            volumes[token] = self.get_volume(token)
        return volumes


    def get_positive_volumes(self):
        return dict([(k, v) for k, v in self.get_volumes().items() if v > 0])


    def get_long_only_volumes(self):
        return dict([(k, v) for k, v in self.get_positive_volumes().items() if self.is_long_only(k)])


    def get_negative_volumes(self):
        return dict([(k, v) for k, v in self.get_volumes().items() if v < 0])


    def get_short_only_volumes(self):
        return dict([(k, v) for k, v in self.get_negative_volumes().items() if self.is_short_only(k)])


    def is_long_only(self, token):
        return all([(True if volume > 0 else False) for _, _, volume in self.get_trades(token)])


    def is_short_only(self, token):
        return all([(True if volume < 0 else False) for _, _, volume in self.get_trades(token)])

    # __dict__
    def get_trade_table(self):
        table = {}
        for token in self.token_list:
            for _ in self.get_trades(token, include_hash=True):
                (trade_hash, trade) = _
                if table.get(trade_hash):
                    table[trade_hash].append(trade)
                else:
                    table[trade_hash] = [trade]
        return table
   
    def get_cumulative_balances(self, token):
        trades = self.get_trades(token)
        balance = 0
        for trade in trades:
            *_, value = trade
            balance += value
            yield trade + (balance,)

    def get_trade_balance_changes(self, token):
        balances = self.get_cumulative_balances(token)
        try:
            *_, initial_balance = next(balances)
        except StopIteration:
            yield 0
        for *_, balance in balances:
            change = (balance - initial_balance) / initial_balance
            initial_balance = balance
            yield change


    def get_variance(self, token):
        changes = list(self.get_trade_balance_changes(token))
        try:
            mean = sum(changes) / len(changes)
        except ZeroDivisionError:
            return 0
        variance = 0
        for change in changes:
            variance += (change - mean) ** 2
        variance /= len(changes)
        return variance


    def get_standard_deviation(self, token):
        return math.sqrt(self.get_variance(token)) 


    def get_skew(self, token):
        changes = list(self.get_trade_balance_changes(token))
        sample_size = len(changes)
        try:
            mean = sum(changes) / sample_size
            skew = 0
            for change in changes:
                skew += (change - mean) ** 3
            sd = self.get_standard_deviation(token)
            skew /= ((sample_size - 1) * (sd ** 3))
            return skew
        except ZeroDivisionError:
            return 0


class Trade:
    def __init__(self):
        self.transactions = transactions


    def __dict__(self):
        return dict([(x['txHash'], tx) for tx in self.transactions])


    def get_tx_by_hash(self, tx_hash):
        return self.__dict__().get(tx_hash, {})

