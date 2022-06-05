import test

zs_address = '0xd5d5a7cb1807364cde0bad51d0a7d758943ab114'
zs = test.Wallet(zs_address)
cream = zs.get_trade_info_for_token('CREAM')

try:
    print(next(cream))
    time.sleep(0.5)
except:
    pass

