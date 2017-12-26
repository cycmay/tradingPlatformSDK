import accountConfig
import requests
import time
import hashlib
import hmac
import json
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
# coolcoin 网址
ENDPOINT = "https://www.coolcoin.com"

def coolcoin_service(key_index='USD_2'):
    access_key = accountConfig.POLONIEX[key_index]['ACCESS_KEY']
    secret_key = accountConfig.POLONIEX[key_index]['SECRET_KEY']
    return Client_Coolcoin(access_key, secret_key)

def formatNumber(x):
    if isinstance(x, float):
        return "{:.8f}".format(x)
    else:
        return str(x)

class Client_Coolcoin():
    def __init__(self, access_key, secret_key,):
        self._public_key = access_key
        self._private_key = secret_key
        self.ssion = requests.Session()
        self.adapter = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=5, max_retries=5)
        self.ssion.mount('http://', self.adapter)
        self.ssion.mount('https://', self.adapter)

    def compatible(self,symbol):
        """
        调整数字货币名字
        :param symbol: 传入的数字货币交易pair
        :return: 输出符合poloniex交易平台命名规则的pair
        """
        symbol = symbol.split('_')[0]

        if 'usd' in symbol:
            symbol = symbol.replace('usd', 'usdt')
        return symbol
    #http请求
    def http_request(self, method, path, params=None):
        """
        适用于public的api接口请求
        :param method: 请求方式：POST/GET
        :param path: 请求路径
        :param params: 请求参数dict
        :return: 返回json格式的响应
        """
        #print("params: \n {}".format(params))
        path = ENDPOINT + path
        response = self.ssion.request(method, path, params=params)
        return response.json()

    def signedRequest(self, method="POST", path='', params={}):
        """
        nonce 可以理解为一个递增的整数：http://zh.wikipedia.org/wiki/Nonce
        key 是申请到的公钥
        signature是签名，是将amount price type nonce key等参数通过'&'字符连接起来通过md5(私钥)
        为key进行sha256算法加密得到的值.
        :param method:
        :param path:
        :param params:
        :return:
        """
        _nonce = int(time.time() * 1000)
        query = urlencode(params)
        query += "&nonce={}".format(_nonce)
        query += "&key={}".format(self._public_key)

        query = query.strip('&')
        print(query)
        # md5(私钥)
        def _getHash(s):
            m = hashlib.md5()
            m.update(s)
            return m.hexdigest()
        secret = bytes(self._private_key.encode("utf-8"))
        md5 = _getHash(secret)
        #print(type(md5))
        msg = query.encode('utf-8')
        key = md5.encode('utf-8')

        signature = hmac.new(key, msg,
                             digestmod=hashlib.sha256).hexdigest()
        #print(signature, '\n')

        params['nonce'] = _nonce
        params['key'] = self._public_key
        params['signature'] = signature
        path = ENDPOINT + path
        print(params, '\n',path)
        response = requests.request(method, path, data=params)
        data = json.loads(response.content)

        return data
    def get_depth(self, coinPairs, **kwargs):
        """
        Path：/api/v1/depth/

        Request类型：GET
        返回JSON dictionary
        asks - 委买单[价格, 委单量]，价格从高到低排序
        bids - 委卖单[价格, 委单量]，价格从高到低排序
        :param coinPairs: 
        :param kwargs: 
        :return: 
        """
        coin, orderType = coinPairs.split('_')

        #coin = self.compatible(coin)
        try:
            params = {
                "coin": coin,
                }
            params.update(kwargs)
            data = self.http_request("GET", "/api/v1/depth/", params)
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
            }
            path = "/api/v1/balance/"
            data = self.signedRequest("POST", path, params=params)
            data = data['data']
            # print(data)
            # 本站返回balance无usd，cny
            balance = {'asset': {'total': 0, 'net': 0},
                       'trade': {'btc': 0, 'usd': 0, 'cny': 0, 'eth': 0, 'ltc': 0, 'etc': 0},
                       'frozen': {'btc': 0, 'usd': 0, 'cny': 0, 'eth': 0, 'ltc': 0, 'etc': 0}}

            # 获取键值
            balance_trade_keys= balance['trade'].keys()
            balance_frozen_keys = balance['frozen'].keys()

            data['usd_balance'] = data['usd_lock'] = 0
            data['cny_balance'] = data['usd_lock'] = 0
            for i in balance_trade_keys:
                balance['trade'][i] = data[i+'_balance']
            for i in balance_frozen_keys:
                balance['frozen'][i] = data[i+'_lock']
                #print(balance)
                return balance
        except Exception as e:
            return e

    def trade(self, trade_type, amount, price, coin, test=False):
        """
        Path：/api/v1/trade_add/
        Request类型：POST
        参数
        key - API key
        signature - signature
        nonce - nonce
        amount - 购买数量
        price - 购买价格
        type - 买单或者卖单
        coin - eth
        返回JSON dictionary
        id - 挂单ID
        result - true(成功), false(失败)
        返回结果示例：
        {"result":true, "id":"11"}
        Send in a new order.
        :param trade_type: 交易市场类型
        :param amount: 交易数量
        :param price: 交易价格
        :param symbol: 数字货币类型
        :param test:
        :return:
        """
        #symbol = self.compatible(symbol)
        coin = coin.split('_')[0]
        side, type = trade_type.split('_')

        params = {
            'amount': amount,
            'price': price,
            'type': side,
            'coin': coin,
        }
        #print(params)
        path = "/api/v1/trade_add/"
        data = self.signedRequest("POST", path, params)
        def _codeErro(code):
            switcher = {
                '100': '必选参数不能为空',
                '101': '非法参数',
                '102': '请求的虚拟币不存在',
                '103': '密钥不存在',
                '104': '签名不匹配',
                '105': '权限不足',
                '106': '请求过期(nonce错误)',
                '200': '余额不足',
                '201': '买卖的数量小于最小买卖额度',
                '202': '下单价格必须在0 - 1000000之间',
                '203': '订单不存在',
                '204': '挂单金额必须在 0.001BTC 以上',
                '205': '限制挂单价格',
                '206': '小数位错误',

            }
            return switcher.get(code, "None")
        if not data['code']:
            return data
        else:
            return data['code']

    def cancel(self, orderID, coin, **kwargs):
        """
        Path：/api/v1/trade_cancel/
        id - 挂单ID
        coin - eth
        :param orderNumber:
        :param currencyPair:
        :param kwargs:
        :return:
        """

        coin = coin.split('_')[0]

        params = {
            'id': int(orderID),
            'coin': coin,
        }
        #print(params)
        path = "/api/v1/trade_cancel/"
        data = self.signedRequest("POST", path, params)
        return data

    def openOrders(self, coin, **kwargs):
        """
                您指定时间后的挂单，可以根据类型查询，比如查看正在挂单和全部挂单
        Path：/api/v1/trade_list/
        Request类型：POST
        参数
        key - API key
        signature - signature
        nonce - nonce
        since - unix timestamp(utc timezone) default == 0, i.e. 返回所有
        coin - eth
        type - 挂单类型[open:正在挂单, all:所有挂单]
        返回JSON dictionary
        id - 挂单ID
        coin - eth
        datetime - date and time
        type - "buy" or "sell"
        price - price
        amount_original - 下单时数量
        amount_outstanding - 当前剩余数量
        :param symbol:
        :param kwargs:
        :return:
        """
        coin = coin.split('_')[0]

        params = {
            'coin': coin,
            'type': 'open', # 默认open
        }
        #print(params)
        orderId = None
        path = "/api/v1/trade_list/"
        data = self.signedRequest("POST", path, params)
        data = data['data']
        if data:
            return data
        else:
            return None

    def cancel_all(self, order_id_list=None, coin ='ETH_BTC'):
        """

        :param order_id_list:
        :param currencyPair:
        :return:
        """
        coin = self.compatible(coin)

        if order_id_list:
            for i in order_id_list:
                try:
                    result = self.cancel(orderID=i, coin=coin)
                    print(result)
                except:
                    continue
        else:
            order_id_list=[]
            openOrders = self.openOrders(coin)
            for i in openOrders:
                if type(i) == type({}):
                    order_id_list.append(i['id'])
                    #print(order_id_list)
            for i in order_id_list:
                try:
                    result = self.cancel(orderID=i, coin=coin)
                    print(result)
                except Exception as e:
                    print(e)


def main():
    print(coolcoin_service().balance())
    #print(coolcoin_service().trade("buy_LIMIT", 0.002, 0.002, "ltc_btc"))
    #print(coolcoin_service().cancel('11', 'eth'))
    #print(coolcoin_service().openOrders('etc'))
if __name__ == '__main__':
    main()