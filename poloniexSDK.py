#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import requests
import hmac
import hashlib
import urllib.parse
import json
import time
import accountConfig

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

# poloniex 网址
ENDPOINT = "https://poloniex.com"

def poloniex_service(key_index='USD_1'):
    access_key = accountConfig.POLONIEX[key_index]['ACCESS_KEY']
    secret_key = accountConfig.POLONIEX[key_index]['SECRET_KEY']
    return Client_Poloniex(access_key, secret_key)
def formatNumber(x):
    if isinstance(x, float):
        return "{:.8f}".format(x)
    else:
        return str(x)

class Client_Poloniex():
    def __init__(self, access_key, secret_key,):
        self._public_key = access_key
        self._private_key = secret_key
        self.ssion = requests.Session()
        self.adapter = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=5, max_retries=5)
        self.ssion.mount('http://', self.adapter)
        self.ssion.mount('https://', self.adapter)

    def compatible(self,symbol):
        if symbol == 'all':
            return symbol
        else:
            symbol = symbol.upper()
            if 'USD' in symbol:
                symbol = symbol.replace('USD', 'BITUSD')
            if 'CNY' in symbol:
                symbol = symbol.replace('CNY', 'BITCNY')

            return symbol

    #http请求
    def http_request(self, method, path, params=None):
        response = self.ssion.request(method, ENDPOINT + path, params=params)
        return response.json()
    #apikey验证登录
    def signedRequest(self, method="POST", path='tradingApi', params={}):
        """
        All calls to the trading API are sent via HTTP POST to https://poloniex.com/
        tradingApi and must contain the following headers:
        Key - Your API key.
        Sign - The query's POST data signed by your key's "secret" according to the
        HMAC-SHA512 method.
        Additionally, all queries must include a "nonce" POST parameter. The nonce
        parameter is an integer which must always be greater than the previous nonce
        used.

        All responses from the trading API are in JSON format. In the event of an
        error, the response will always be of the following format:

       """

        url = ENDPOINT + path
        Key = self._public_key
        payload = {
            'nonce': int(time.time() * 1000),
        }
        payload.update(params)
        print(payload)
        paybytes = urllib.parse.urlencode(payload).encode('utf8')

        # print(paybytes)
        secret = bytes(self._private_key.encode("utf-8"))
        sign = hmac.new(secret, paybytes, hashlib.sha512).hexdigest()

        #print(sign)
        headers = {
            'Key': Key,
            'Sign': sign,
        }
        response = self.ssion.request(method, url, headers=headers, data=payload)
        data = json.loads(response.text)
        #print(data)
        return data


    def get_depth(self, currencyPair, **kwargs):
        """get order book
        Returns the order book for a given market, as well as a sequence number for
        use with the Push API and an indicator specifying whether the market is frozen.
        You may set currencyPair to "all" to get the order books of all markets.
        command=returnOrderBook&currencyPair=BTC_NXT&depth=10
        """

        currencyPair = self.compatible(currencyPair)
        try:
            params = {"command":"returnOrderBook","currencyPair": currencyPair, "depth": "25"}
            params.update(kwargs)
            data = self.http_request("GET", "/public", params)
            #print(data)
            bids = []
            asks = []
            #isFrozen = []
            for i in data['bids']:
                bids.append([float(i[0]), float(i[1])])
            for i in data['asks']:
                asks.append([float(i[0]), float(i[1])])
            depth = {'bids': bids, 'asks': asks}

            return depth
        except Exception as e:
            time.sleep(0.1)
            print(e)


    def balance(self):
        """
        Used to retrieve all balances from your account
        """
        try:
            params = {
                "command": "returnCompleteBalances",
                "account": "all"
            }
            path = "/tradingApi"
            data = self.signedRequest("POST", path, params=params)
            #print(data)

            balance = {'asset': {'total': 0, 'net': 0},
                       'trade': {'btc': 0, 'usd': 0, 'cny': 0, 'eth': 0, 'ltc': 0, 'etc': 0},
                       'frozen': {'btc': 0, 'usd': 0, 'cny': 0, 'eth': 0, 'ltc': 0, 'etc': 0}}

            #获取键值
            balance_trade_keys= balance['trade'].keys()
            balance_frozen_keys = balance['frozen'].keys()
            """
            BITUSD BITCNY 不一样
            
            """

            data['USD'] = data.pop('BITUSD')
            data['CNY'] = data.pop('BITCNY')
            for i in balance_trade_keys:
                balance['trade'][i] = data[i.upper()]['available']
            for i in balance_frozen_keys:
                balance['frozen'][i] = data[i.upper()]['onOrders']

            #print(balance)
            return balance


        except Exception as e:
            return e

    def trade(self, trade_type, amount, price, symbol, test=False):
        """
        trade(self, symbol, side, quantity, price, orderType=LIMIT, timeInForce=GTC,
        test=False, **kwargs):
        Send in a new order.
        :return:

        """
        symbol = self.compatible(symbol)
        side, orderType = trade_type.split('_')
        orderType = orderType.upper()
        params = {
            'command': side,
            'currencyPair': symbol,
            'rate': formatNumber(price),
            'Amount': str(amount),
        }
        #print(params)
        path = "/tradingApi"

        data = self.signedRequest("POST", path, params)
        return data
    def cancel(self, orderNumber, currencyPair, **kwargs):
        """Cancel an active order.
                Args:
                    symbol (str)
                    orderId (int, optional)
                    origClientOrderId (str, optional)
                    newClientOrderId (str, optional): Used to uniquely identify this
                        cancel. Automatically generated by default.
                    recvWindow (int, optional)
        """
        currencyPair = self.compatible(currencyPair)
        params = {
            "command": "cancelOrder",
            'currencyPair': currencyPair,
            'orderNumber': orderNumber,
            }
        params.update(kwargs)
        #print(params)
        path = "/tradingApi"
        data = self.signedRequest("POST", path, params)
        return data

    def openOrders(self, symbol='all', **kwargs):
        """
        Returns your open orders for a given market, specified by the "currencyPair"
        POST parameter, e.g. "BTC_XCP". Set "currencyPair" to "all" to return open
        orders for all markets

        :return:
        """
        path = "/tradingApi"
        currencyPair = self.compatible(symbol)

        params = {
            "command": "returnOpenOrders",
            "currencyPair": currencyPair
            }
        params.update(kwargs)
        #print(params)
        data = self.signedRequest("POST", path, params)
        return data

    def cancel_all(self, order_id_list=None, currencyPair ='ETH_BTC'):
        """

        :param order_id_list:
        :param currencyPair:
        :return:
        """
        currencyPair = self.compatible(currencyPair)

        if order_id_list:
            for i in order_id_list:
                try:
                    result = self.cancel(orderNumber=i, currencyPair=currencyPair)
                    print(result)
                except:
                    continue
        else:
            order_id_list=[]
            openorders = self.openOrders(currencyPair)
            for i in openorders:
                if type(i) == type({}):
                    order_id_list.append(i['orderId'])
                    #print(order_id_list)
            for i in order_id_list:
                try:
                    result = self.cancel(orderNumber=i, currencyPair=currencyPair)
                    print(result)
                except:
                    continue

def main():
    #print(poloniex_service().get_depth("btc_xvc"))

    #print(poloniex_service().trade("sell_LIMIT",1.00077106,0.01,"BTC_XVC"))
    print(poloniex_service().cancel("31226040",'BTC_XCP'))
    #print(poloniex_service().openOrders())
    #print(poloniex_service().cancel_all())
    pass
if __name__ == '__main__':
    main()

