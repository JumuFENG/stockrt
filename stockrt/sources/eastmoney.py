# coding:utf8
import re
import time
import json
from . import rtbase

'''
quotes:
一次请求多只股票，无买卖5档行情
https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.601136&fields=f2,f12

一次请求一只股票, 买卖5档行情
https://hsmarketwg.eastmoney.com/api/SHSZQuoteSnapshot?id=601136&callback=

这个接口也可以获取实时买卖5档行情, 价格都是整数
"https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=1&cb=&secid=%s&fields="
"f19,f17,f531,f15,f13,f11,f20,f18,f16,f14,f12,f39,f37,f35,f33,f31,f40,f38,f36,f34,f32,"
"f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f71,f84,"
"f85,f116,f117"

tline:
http://push2his.eastmoney.com/api/qt/stock/trends2/get?fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&fields2=f51,f52,f53,f54,f55,f56,f57,f58&secid=1.603536&ndays=1&iscr=1&iscca=0

kline:
https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.601136&klt=101&fqt=1&lmt=100&end=20500000&iscca=1&fields1=f1,f2,f3,f4,f5,f6,f7,f8&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61
&ut=f057cbcbce2a86e2866ab8877db1d059&forcect=1

'''


class EastMoney(rtbase.rtbase):
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
            'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=%s&klt=%d&fqt=1&lmt=%d'
            '&end=20500000&iscca=1&fields1=f1,f2,f3,f4,f5,f6,f7,f8'
            '&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64'
        )

    @property
    def dklineapi(self):
        return self.mklineapi

    @staticmethod
    def get_secid(code):
        return code.replace('sh', '1.').replace('sz', '0.').replace('bj', '0.')

    @classmethod
    def secid_to_fullcode(cls, sec):
        return f'sh{sec[-6:]}' if sec.startswith('1.') else cls.get_fullcode(sec[-6:])

    def get_quote_url(self, stocks):
        return self.qtapi % (','.join([ self.get_secid(stock) for stock in stocks]))

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
        return self.qt5api % stock[-6:]

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
            }
        return stock_dict

    def get_tline_url(self, stock):
        return self.tlineapi % self.get_secid(stock)

    def format_tline_response(self, rep_data):
        stock_dict = {}
        for code, rsp in rep_data:
            stocks_detail = json.loads(rsp)
            stock_dict[code] = [
                {
                    'time': time_str.split()[1],
                    'price': float(price),
                    'volume': int(volume) * 100,
                    'amount': float(amount),
                    'avg_price': float(avg_price),
                }
                for kl in stocks_detail['data']['trends']
                for time_str, _, price, *_, volume, amount, avg_price in [kl.split(',')]
            ]
        return stock_dict

    def get_mkline_url(self, stock, kltype='1', length=320):
        return self.mklineapi % (self.get_secid(stock), kltype, length)

    def format_kline_response(self, rep_data, is_minute=False, withqt=False):
        stock_dict = dict()
        for code, rsp in rep_data:
            stocks_detail = json.loads(rsp)
            klines = stocks_detail['data']['klines']
            klarr = []
            for kline in klines:
                kdata = kline.split(',')
                klarr.append({
                    'time': kdata[0],
                    'open': self._safe_price(kdata[1]),
                    'close': self._safe_price(kdata[2]),
                    'high': self._safe_price(kdata[3]),
                    'low': self._safe_price(kdata[4]),
                    'volume': int(kdata[5]) * 100,
                    'amount': float(kdata[6]),
                    'amplitude': self._safe_price(kdata[7])/100,
                    'change': self._safe_price(kdata[8])/100,
                    'change_px': self._safe_price(kdata[9]),
                    'turnover': self._safe_price(kdata[10])/100})
            stock_dict[code] = klarr

        return stock_dict

    def get_dkline_url(self, stock, kltype='101', length=320):
        return self.dklineapi % (self.get_secid(stock), kltype, length)

