# coding:utf8
import re
import time
import json
from . import rtbase

'''

https://hsmarketwg.eastmoney.com/api/SHSZQuoteSnapshot?id=601136&callback=
https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.601136&fields=f2,f12

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
        return (
            "https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=1&cb=&secid=%s&fields="
            "f19,f17,f531,f15,f13,f11,f20,f18,f16,f14,f12,f39,f37,f35,f33,f31,f40,f38,f36,f34,f32,"
            "f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f71,f84,"
            "f85,f116,f117"
        )

    @property
    def tlineapi(self):
        return ('')

    @property
    def mklineapi(self):
        return ('')

    @property
    def dklineapi(self):
        return None

    @staticmethod
    def get_secid(code):
        return code.replace('sh', '1.').replace('sz', '0.').replace('bj', '0.')

    @staticmethod
    def secid_to_fullcode(sec):
        return f'sh{sec[-6:]}' if sec.startswith('1.') else rtbase.get_fullcode(sec[-6:])

    def get_quote_url(self, stocks):
        return self.qtapi % (','.join([ self.get_secid(stock) for stock in stocks]))

    def format_quote_response(self, rep_data):
        stock_dict = dict()
        for _, rsp in rep_data:
            stocks_detail = json.loads(rsp)
            for stock in stocks_detail['data']['diff']:
                fcode = self.secid_to_fullcode(f"{stock['f13']}.{stock['f12']}")
                stock_dict[fcode] = {
                    'name': stock['f14'],
                    'close': self._safe_price(stock['f2']),
                    'last_px': self._safe_price(stock['f2']),
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
        return self.qt5api % self.get_secid(stock)

    def quotes5(self, stocks):
        return self._fetch_concurrently(stocks, self.get_quote5_url, self.format_quote5_response)

    def format_quote5_response(self, rep_data):
        stock_dict = dict()
        for code, rsp in rep_data:
            stocks_detail = json.loads(rsp)
            stock = stocks_detail['data']
            stock_dict[code] = {
                'name': stock['f58'],
                'close': self._safe_price(stock['f43']) / 100,
                'last_px': self._safe_price(stock['f43']) / 100,
                # 'change': self._safe_price(stock['f3']) / 100, # 涨跌幅
                # 'change_px': self._safe_price(stock['f4']), # 涨跌额
                'volume': self._safe_price(stock['f47']) * 100,
                'amount': self._safe_price(stock['f48']),
                'high': self._safe_price(stock['f44']) / 100,
                'low': self._safe_price(stock['f45']) / 100,
                'open': self._safe_price(stock['f46']) / 100,
                'lclose': self._safe_price(stock['f60']) / 100,
                "mc": self._safe_price(stock['f116']),
                "cmc": self._safe_price(stock['f117']),
                "bid5": self._safe_price(stock['f11']) / 100,
                "bid5_volume": self._safe_price(stock['f12']) * 100,
                "bid4": self._safe_price(stock['f13']) / 100,
                "bid4_volume": self._safe_price(stock['f14']) * 100,
                "bid3": self._safe_price(stock['f15']) / 100,
                "bid3_volume": self._safe_price(stock['f16']) * 100,
                "bid2": self._safe_price(stock['f17']) / 100,
                "bid2_volume": self._safe_price(stock['f18']) * 100,
                "bid1": self._safe_price(stock['f19']) / 100,
                "bid1_volume": self._safe_price(stock['f20']) * 100,
                "ask1": self._safe_price(stock['f31']) / 100,
                "ask1_volume": self._safe_price(stock['f32']) * 100,
                "ask2": self._safe_price(stock['f33']) / 100,
                "ask2_volume": self._safe_price(stock['f34']) * 100,
                "ask3": self._safe_price(stock['f35']) / 100,
                "ask3_volume": self._safe_price(stock['f36']) * 100,
                "ask4": self._safe_price(stock['f37']) / 100,
                "ask4_volume": self._safe_price(stock['f38']) * 100,
                "ask5": self._safe_price(stock['f39']) / 100,
                "ask5_volume": self._safe_price(stock['f40']) * 100,
            }
        return stock_dict

    def get_tline_url(self, stock):
        return self.tlineapi % self.get_secid(stock)
    
    def get_mkline_url(self, stock, kltype='1', length=320):
        return self.mklineapi % (self.get_secid(stock), kltype, length)
    
    def get_dkline_url(self, stock, kltype='101', length=320):
        return self.dklineapi % (self.get_secid(stock), kltype, length)
