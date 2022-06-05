import configparser
import os

def get_config(path=None):
    if not path:
        path = os.path.join(os.path.expanduser('~'), 'cspan.ini')
    parser = configparser.ConfigParser()
    config = parser.read(path)
    return parser

def get_etherscan_api_key():
    return get_config()['etherscan']['api_key']

