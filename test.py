import configparser
import os
import json
import glob
import time
import math

from datetime import datetime, timedelta
from etherscan import Etherscan
from pycoingecko import CoinGeckoAPI
from pathlib import Path
from collections import namedtuple

parser = configparser.ConfigParser()
config = parser.read(os.path.join(os.path.expanduser('~'), 'cspan.ini'))
etherscan_key = parser['etherscan']['api_key']

etherscan_api = Etherscan(etherscan_key)
coingecko_api = CoinGeckoAPI()
coingecko_list = coingecko_api.get_coins_list()

Transaction = namedtuple("Transaction", "hash timestamp value")

def run_trades(wallet, symbol, interval=0.1):
    for t in wallet.get_trade_info_for_token(symbol):
        l = list(t)
        timestamp = l[2]
        l[2] = get_timestamp_from_unix(timestamp)
        t = tuple(l)
        print(t[0:4])
        time.sleep(interval) 

class User:
    def __init__(self, name, wallets):
        self.name = name
        self.wallets = wallets



class Token:
    def __init__(self, address, symbol, decimal):
        self.address = address
        self.symbol = symbol
        self.decimal = decimal

    @classmethod
    def get_token_for_transaction(cls, transaction):
        return cls(transaction['contractAddress'],
            transaction['tokenSymbol'], transaction['tokenDecimal'])


def get_timestamp_from_unix(unix):
    return datetime.fromtimestamp(int(unix)).strftime("%m/%d/%Y, %H:%M:%S")

class Wallet:
    def __init__(self, address, name=''):
        self.address = address
        self.name = name
        self._token_list = None

    @property
    def token_list(self):
        if self._token_list is None:
            self._token_list = self.get_tokens_from_history()
        return self._token_list

    def get_token_balances(self):
        balances = {}
        for symbol, token in self.token_list.items():
            balance = get_converted_token_balance(self.address, token.address, token.decimal)
            balances[symbol] = balance
        return balances

    def save_transaction_history(self, remove=False, start=timedelta(weeks=(4 * 3))):
        if remove:
            for path in glob.glob(f"{self.address}/*"):
                os.remove(path)
        Path(self.address).mkdir(parents=False, exist_ok=True)
        timestamp = datetime.utcnow() - start
        timestamp = round(timestamp.timestamp())
        with open(f"{self.address}/{timestamp}", 'w') as f:
            json.dump(get_address_transactions_from_date(self.address, timestamp), f)
            

    def get_last_saved_block(self):
        paths = glob.glob(f"{self.address}/*")
        try:
            with open(paths[0], 'r') as f:
                return json.load(f)[-1]['blockNumber']
        except:
            return None

    def read_transaction_history(self):
        paths = glob.glob(f"{self.address}/*")
        print(f"Paths {paths}")
        transactions = []
        for path in paths:
            try:
                with open(path, 'r') as f:
                    transactions += json.load(f)
            except json.decoder.JSONDecodeError:
                continue
        return transactions

    def get_tokens_from_history(self):
        paths = glob.glob(f"{self.address}/*")
        tokens = {}
        for path in paths:
            try:
                with open(path, 'r') as f:
                    for t in json.load(f):
                        if not tokens.get(t['tokenSymbol']):
                            tokens[t['tokenSymbol']] = Token.get_token_for_transaction(t)
            except json.decoder.JSONDecodeError:
                continue
        return tokens

    def get_transactions_for_token(self, symbol, reverse=False):
        history = self.read_transaction_history()
        token_transactions = list(filter(lambda d: d['tokenSymbol'] == symbol, history))
        if reverse:
            token_transactions = reversed(token_transactions)
        for transaction in token_transactions:
            value = convert_token_balance(transaction['value'], transaction['tokenDecimal'], 4)
            if transaction['from'] == self.address:
                value *= -1
            timestamp = int(transaction['timeStamp'])
            #timestamp = datetime.fromtimestamp(int(transaction['timeStamp'])).strftime("%m/%d/%Y, %H:%M:%S")
            yield Transaction(transaction['hash'], timestamp, value)

    def get_trade_info_for_token(self, symbol, min_ratio=1, reverse=False):
        cumulative_balance = 0
        max_balance = 0
        count = 0
        percent = 0
        for transaction in self.get_transactions_for_token(symbol, reverse):
            if cumulative_balance == 0:
                count += 1
            value = transaction.value
            last_balance = cumulative_balance
            cumulative_balance += round(value)
            try:
                percent = (last_balance - cumulative_balance) / last_balance
                percent *= -100
                percent = round(percent, 2)
            except ZeroDivisionError:
                percent = "N/A"
            max_balance = max(max_balance, cumulative_balance)
            yield count, transaction.hash, transaction.timestamp, transaction.value, cumulative_balance, percent 

    def is_long_only(self, symbol):
        long_only = True
        for info in self.get_trade_info_for_token(symbol):
            _, _, _, value, _, _ = info
            if value < 0:
                long_only = False
                break
        return long_only
       
    def get_long_only_trades(self):
        long_only = []
        for token in self.token_list.keys():
            if self.is_long_only(token):
                long_only.append(token)
        return long_only

    def get_latest_trade(self, symbol):
        latest_trade = []
        for info in reversed(list(self.get_trade_info_for_token(symbol))):
            _, _, _, _, _, percent = info
            if percent == "N/A":
                latest_trade.append(info)
                break
            latest_trade.append(info)
        return latest_trade

    def get_latest_trade_for_all(self):
        latest_trades = {}
        for token in self.token_list.keys():
            latest_trades[token] = self.get_latest_trade(token)
        return [(k, get_timestamp_from_unix(v)) for k,v in sorted([(t[0], t[1][-1][2]) for t in latest_trades.items()], key=lambda t: t[1])]


def get_latest_trades_for_addresses(wallets):
    trades = {}
    for wallet in wallets:
        # TODO: Add name to Wallet
        address = wallet.address
        try:
            print(f"Downloading transactions for {address}")
            wallet.save_transaction_history()
            print(f"Compiling trades for {address}")
            trades[address] = wallet.get_latest_trade_for_all()
        except Exception as e:
            print(e)
            print(f"Skipping for {address}")
    return trades

    
def get_block_number(timestamp=None):
    if not timestamp:
        timestamp = round(time.time())
    return etherscan_api.get_block_number_by_timestamp(timestamp=timestamp, closest='before')


def get_address_transactions_from_date(address, timestamp):
    startblock = get_block_number(timestamp=timestamp)
    endblock = get_block_number()
    all_transactions = []
    finished = False
    while not finished:
        print(f"INFO: Using startblock {startblock} and endblock {endblock}")
        transactions = etherscan_api.get_erc20_token_transfer_events_by_address(address=address, 
            startblock=startblock, endblock=endblock, sort='asc')
        print(f"Transaction Count: {len(transactions)}")
        all_transactions += transactions
        lastblock = transactions[-1]['blockNumber']
        if len(transactions) != 10000:
            finished = True
        else:
            startblock = lastblock
    return all_transactions

def convert_token_balance(balance, decimal, places):
    return round(int(balance) * pow(10, -1 * int(decimal)), places)

def get_token_balance(address, token_address):
    return etherscan_api.get_acc_balance_by_token_and_contract_address(contract_address=token_address, address=address)

def get_converted_token_balance(address, token_address, decimal, places=4):
    balance = get_token_balance(address, token_address)
    return convert_token_balance(balance, decimal, places)

def download_transaction_history(address):
    timestamp = datetime.utcnow().strftime('%s')
    path = f"{timestamp}_{address}.json"
    with open(path, 'w') as f:
        json.dump(get_transaction_history(address), f)

def get_local_transaction_history(address):
    paths = glob.glob(f"*{address}.json")
    latest = sorted(paths, key=lambda p: os.stat(p).st_ctime, reverse=True)[-1]
    with open(latest, 'r') as f:
        return json.load(f)

def get_token_info_from_history(address, keys=['contractAddress', 'tokenDecimal']):
    transactions = get_local_transaction_history(address)
    info = {}
    for transaction in transactions:
        symbol = transaction['tokenSymbol']
        if not info.get(symbol):
            info[symbol] = dict(map(lambda k: (k, transaction[k]), keys))
    return info
        

def get_token_balances(address):
    balances = {}
    for symbol, info in get_token_info_from_history(address).items():
        balance = get_converted_token_balance(address, info['contractAddress'],
            info['tokenDecimal']) 
        if balance != 0:
            balances[symbol] = balance
        time.sleep(1)
    return balances 


def get_token_balances_for_addresses(addresses):
    balances = {}
    for address in addresses:
        try:
            balances[address] = get_token_balances(address)
        except Exception as e:
            balances[address] = e
    return balances


def get_dollar_prices_for_tokens(token_list):
    list_info = list(filter(lambda d: d['symbol'].upper() in [t.upper() for t in token_list], coingecko_list))
    id_string = ','.join(set(map(lambda d: d['id'], list_info)))
    return coingecko_api.get_price(ids=id_string, vs_currencies='usd')
  

