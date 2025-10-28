# coding:utf8
import re
import os
import hashlib
import time
import json
import requests
from functools import lru_cache
from .rtbase import requestbase

'''
quotes:
一次请求多只股票，无买卖5档行情
https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.601136&fields=f2,f12

一次请求一只股票, 买卖5档行情
https://hsmarketwg.eastmoney.com/api/SHSZQuoteSnapshot?id=601136&callback=

这个接口也可以获取实时买卖5档行情
"https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=2&cb=&secid=%s&fields="
"f19,f17,f531,f15,f13,f11,f20,f18,f16,f14,f12,f39,f37,f35,f33,f31,f40,f38,f36,f34,f32,"
"f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f71,f84,"
"f85,f116,f117"

tline:
http://push2his.eastmoney.com/api/qt/stock/trends2/get?fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&fields2=f51,f52,f53,f54,f55,f56,f57,f58&secid=1.603536&ndays=1&iscr=1&iscca=0

kline:
https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.601136&klt=101&fqt=1&lmt=100&end=20500000&iscca=1&fields1=f1,f2,f3,f4,f5,f6,f7,f8&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61
&ut=f057cbcbce2a86e2866ab8877db1d059&forcect=1

股票列表-涨幅榜
https://quote.eastmoney.com/center/gridlist.html#hs_a_board
https://push2.eastmoney.com/api/qt/clist/get?np=1&fltt=2&invt=2&cb=&fs=m:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2,m:0+t:81+s:2048&fields=f1,f2,f3,f4,f5,f6,f15,f16,f17,f12,f13,f14,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f124&fid=f3&pn=2&pz=20&po=1&dect=1&ut=fa5fd1943c7b386f172d6893dbfba10b&wbp2u=|0|0|0|web&_=1761043426715

请求限制: 1000/5min 50000/24h
'''

class EmCookie:
    cookies = []
    @classmethod
    def get_cookie(cls):
        # 50000/24h, 500/5min (这里减半)
        cls.cookies = [c for c in cls.cookies if c['total_used'] < 50000]
        for cookie in cls.cookies:
            if time.time() - cookie['timestamp'] > 300:
                cookie['timestamp'] = time.time()
                cookie['used'] = 0
        cookie = next((c for c in cls.cookies if c['used'] < 500), None)
        if not cookie:
            cookie = {
                'cookie': cls.generate_cookie(),
                'timestamp': time.time(),
                'used': 0,
                'total_used': 0,
            }
            cls.cookies.append(cookie)
        cookie['used'] += 1
        cookie['total_used'] += 1
        return cookie['cookie']

    @classmethod
    def generate_cookie(cls):
        def random_string(length=21):
            charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890-_'
            random_bytes = os.urandom(length)
            s = ''
            for i in range(length-1, -1, -1):
                index = 63 & random_bytes[i]
                s += charset[index]

            hash_val = hashlib.sha256(s.encode()).hexdigest()
            return s + hash_val[:4]

        url = 'https://anonflow2.eastmoney.com/backend/api/webreport'
        useragent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:144.0) Gecko/20100101 Firefox/144.0'
        payload = {
            "osPlatform":"MacOS","sourceType":"WEB","osversion":"Mac OS X 10","language":"en-US","timezone":"Asia/Shanghai",
            "webDeviceInfo":{
                "screenResolution": "1600X900",
                "userAgent": useragent,
                "canvasKey": hashlib.md5(random_string().encode()).hexdigest(),
                "webglKey": hashlib.md5(random_string().encode()).hexdigest(),
                "fontKey": hashlib.md5(random_string().encode()).hexdigest(),
                "audioKey": hashlib.md5(random_string().encode()).hexdigest(),
            }
        }
        headers = {
            'Host': 'anonflow2.eastmoney.com',
            'User-Agent': useragent,
            'Cookie': f'st_nvi={random_string()}'
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return '; '.join([f'{k}={v}' for k,v in response.json()['data'].items()])


class EastMoney(requestbase):
    quote_max_num = 60
    @property
    def qtapi(self):
        return (
            "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=%s&fields="
            "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f19,f20,f21,f22,f23,f115"
        )

    @property
    def qt5api(self):
        return 'https://hsmarketwg.eastmoney.com/api/SHSZQuoteSnapshot?id=%s&callback='

    @property
    def tlineapi(self):
        return (
            'http://push2his.eastmoney.com/api/qt/stock/trends2/get?fields1='
            'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&fields2=f51,f52,f53,f54,f55,f56,f57,f58'
            '&secid=%s&ndays=1&iscr=1&iscca=0'
        )

    @property
    def mklineapi(self):
        return (
            'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=%s&klt=%d&fqt=%d&lmt=%d'
            '&end=20500000&fields1=f1,f2,f3,f4,f5,f6,f7,f8'
            '&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64'
        )

    @property
    def dklineapi(self):
        return self.mklineapi

    @property
    def fklineapi(self):
        return self.mklineapi + '&beg=0'

    @property
    def stocklistapi(self):
        return (
            "https://push2.eastmoney.com/api/qt/clist/get?np=1&fltt=2&invt=2&cb="
            "&fs=m:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2,m:0+t:81+s:2048"
            "&fields=f1,f2,f3,f4,f5,f6,f15,f16,f17,f12,f13,f14,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f124"
            "&fid=f3&pn=%d&pz=%d&po=1&dect=1&ut=fa5fd1943c7b386f172d6893dbfba10b&wbp2u=|0|0|0|web&_=%d"
        )

    @staticmethod
    def get_secid(code):
        return code.replace('sh', '1.').replace('sz', '0.').replace('bj', '0.')

    @staticmethod
    def get_em_cookie():
        return EmCookie.get_cookie()

    @classmethod
    def secid_to_fullcode(cls, sec):
        return f'sh{sec[-6:]}' if sec.startswith('1.') else cls.get_fullcode(sec[-6:])

    def get_quote_url(self, stocks):
        url = self.qtapi % (','.join([ self.get_secid(stock) for stock in stocks]))
        headers = {
            **self._get_headers(),
            'Referer': 'https://quote.eastmoney.com/',
            'Host': 'push2.eastmoney.com',
            'Cookie': self.get_em_cookie(),
        }
        return url, headers

    def format_quote_response(self, rep_data):
        stock_dict = dict()
        for codes, rsp in rep_data:
            stocks_detail = json.loads(rsp)
            for stock in stocks_detail['data']['diff']:
                fcode = self.secid_to_fullcode(f"{stock['f13']}.{stock['f12']}")
                code = fcode if fcode in codes else stock['f12'] if stock['f12'] in codes else fcode
                stock_dict[code] = {
                    'name': stock['f14'],
                    'price': self._safe_price(stock['f2']),
                    'change': self._safe_price(stock['f3']) / 100, # 涨跌幅
                    'change_px': self._safe_price(stock['f4']), # 涨跌额
                    'volume': self._safe_price(stock['f5']) * 100,
                    'amount': self._safe_price(stock['f6']),
                    'high': self._safe_price(stock['f15']),
                    'low': self._safe_price(stock['f16']),
                    'open': self._safe_price(stock['f17']),
                    'lclose': self._safe_price(stock['f18']),
                    "mc": self._safe_price(stock['f20']),
                    "cmc": self._safe_price(stock['f21']),
                }
        return stock_dict

    def get_quote5_url(self, stock):
        url = self.qt5api % stock[-6:]
        headers = {
            **self._get_headers(),
            'Referer': 'https://quote.eastmoney.com/',
            'Host': 'hsmarketwg.eastmoney.com',
            'Cookie': self.get_em_cookie(),
        }
        return url, headers

    def quotes5(self, stocks):
        return self._fetch_concurrently(stocks, self.get_quote5_url, self.format_quote5_response)

    def format_quote5_response(self, rep_data):
        stock_dict = dict()
        for code, rsp in rep_data:
            stocks_detail = json.loads(rsp)
            rtquote = stocks_detail['realtimequote']
            fivequote = stocks_detail['fivequote']
            stock_dict[code] = {
                'name': stocks_detail['name'],
                'price': self._safe_price(rtquote['currentPrice']),
                'open': self._safe_price(rtquote['open']),
                'high': self._safe_price(rtquote['high']),
                'low': self._safe_price(rtquote['low']),
                'lclose': self._safe_price(fivequote['yesClosePrice']),
                'top_price': self._safe_price(stocks_detail['topprice']),
                'bottom_price': self._safe_price(stocks_detail['bottomprice']),
                'change': self._safe_price(rtquote['zdf'].replace('%', '')) / 100, # 涨跌幅
                'change_px': self._safe_price(rtquote['zd']),
                'volume': self._safe_price(rtquote['volume']) * 100,
                'amount': self._safe_price(rtquote['amount']),
                'turnover': self._safe_price(rtquote['turnover']),
                'avg_price': self._safe_price(rtquote['avg']),
                "bid1": self._safe_price(fivequote['buy1']),
                "bid1_volume": self._safe_price(fivequote['buy1_count']) * 100,
                "bid2": self._safe_price(fivequote['buy2']),
                "bid2_volume": self._safe_price(fivequote['buy2_count']) * 100,
                "bid3": self._safe_price(fivequote['buy3']),
                "bid3_volume": self._safe_price(fivequote['buy3_count']) * 100,
                "bid4": self._safe_price(fivequote['buy4']),
                "bid4_volume": self._safe_price(fivequote['buy4_count']) * 100,
                "bid5": self._safe_price(fivequote['buy5']),
                "bid5_volume": self._safe_price(fivequote['buy5_count']) * 100,
                "ask1": self._safe_price(fivequote['sale1']),
                "ask1_volume": self._safe_price(fivequote['sale1_count']) * 100,
                "ask2": self._safe_price(fivequote['sale2']),
                "ask2_volume": self._safe_price(fivequote['sale2_count']) * 100,
                "ask3": self._safe_price(fivequote['sale3']),
                "ask3_volume": self._safe_price(fivequote['sale3_count']) * 100,
                "ask4": self._safe_price(fivequote['sale4']),
                "ask4_volume": self._safe_price(fivequote['sale4_count']) * 100,
                "ask5": self._safe_price(fivequote['sale5']),
                "ask5_volume": self._safe_price(fivequote['sale5_count']) * 100,
                "date": rtquote['date'][0:4] + '-' + rtquote['date'][4:6] + '-' + rtquote['date'][6:8],
                "time": rtquote['time'],
            }
        return stock_dict

    def get_tline_url(self, stock):
        url = self.tlineapi % self.get_secid(stock)
        headers = {
            **self._get_headers(),
            'Referer': f'https://quote.eastmoney.com/{self.secid_to_fullcode(stock)}.html',
            'Host': 'push2his.eastmoney.com',
            'Cookie': self.get_em_cookie(),
        }
        return url, headers

    def format_tline_response(self, rep_data):
        stock_dict = {}
        for code, rsp in rep_data:
            stocks_detail = json.loads(rsp)
            stock_dict[code] = self.format_array_list([[
                    time_str.split()[1], float(price), int(volume) * 100, float(amount), float(avg_price),
                ]
                for kl in stocks_detail['data']['trends']
                for time_str, _, price, *_, volume, amount, avg_price in [kl.split(',')]
            ], ['time', 'price', 'volume', 'amount', 'avg_price'])
        return stock_dict

    def get_mkline_url(self, stock, kltype='1', length=320, fq=1):
        url = self.mklineapi % (self.get_secid(stock), kltype, fq, length)
        headers = {
            **self._get_headers(),
            'Referer': f'https://quote.eastmoney.com/{self.secid_to_fullcode(stock)}.html',
            'Host': 'push2his.eastmoney.com',
            'Cookie': self.get_em_cookie(),
        }
        return url, headers

    def format_kline_response(self, rep_data, **kwargs):
        stock_dict = dict()
        kcols = ['time', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'change', 'change_px', 'turnover']
        for code, rsp in rep_data:
            stocks_detail = json.loads(rsp)
            klines = stocks_detail['data']['klines']
            klarr = []
            for kline in klines:
                kdata = kline.split(',')
                klarr.append([
                    kdata[0],
                    self._safe_price(kdata[1]),
                    self._safe_price(kdata[2]),
                    self._safe_price(kdata[3]),
                    self._safe_price(kdata[4]),
                    int(kdata[5]) * 100,
                    self._safe_price(kdata[6]),
                    self._safe_price(kdata[7])/100,
                    self._safe_price(kdata[8])/100,
                    self._safe_price(kdata[9]),
                    self._safe_price(kdata[10])/100])
            stock_dict[code] = self.format_array_list(klarr, kcols)

        return stock_dict

    def get_dkline_url(self, stock, kltype='101', length=320, fq=1):
        return self.get_mkline_url(stock, kltype, length, fq)

    def get_fkline_url(self, stock, kltype='101', fq=0):
        url = self.fklineapi % (self.get_secid(stock), kltype, fq, 0)
        headers = {
            **self._get_headers(),
            'Referer': f'https://quote.eastmoney.com/{self.secid_to_fullcode(stock)}.html',
            'Host': 'push2his.eastmoney.com',
            'Cookie': self.get_em_cookie(),
        }
        return url, headers

    def get_stock_list_url(self, page = 1, market = 'all'):
        url = self.stocklistapi % (page, self.count_per_page, int(time.time()*1000))
        headers = {
            **self._get_headers(),
            'Cookie': self.get_em_cookie(),
        }
        return url, headers

    def format_stock_list_response(self, rep_data, market='all'):
        result = {}
        for pg, rsp in rep_data:
            data = json.loads(rsp)['data']['diff']
            for stock in data:
                if stock['f2'] == '-':
                    continue
                fcode = self.secid_to_fullcode(f"{stock['f13']}.{stock['f12']}")
                if pg not in result:
                    result[pg] = []
                result[pg].append({
                    'code': fcode,
                    'name': stock['f14'],
                    'close': float(stock['f2']),
                    'high': float(stock['f15']),
                    'low': float(stock['f16']),
                    'open': float(stock['f17']),
                    'change_px': float(stock['f4']),
                    'change': float(stock['f3']) / 100,
                    'volume': int(stock['f5']) * 100,
                    'amount': float(stock['f6']),
                    'main': float(stock['f62']),
                    'mainp': float(stock['f184']),
                    'small': float(stock['f84']),
                    'middle': float(stock['f78']),
                    'big': float(stock['f72']),
                    'super': float(stock['f66']),
                    'smallp': float(stock['f87']),
                    'midllep': float(stock['f81']),
                    'bigp': float(stock['f75']),
                    'superp': float(stock['f69']),
                })

        result_arr = []
        for i in range(1, len(rep_data) + 1):
            if i in result:
                result_arr.extend(result[i])
        return {market: result_arr}
