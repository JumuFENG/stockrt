# coding:utf8
import re
import time
import json
from typing import Optional
from . import rtbase

"""
reference: https://stockapp.finance.qq.com/mstats/

url 参数改动
股票代码 :sh603444
k线数：320
url = "https://ifzq.gtimg.cn/appstock/app/kline/mkline?param=sh603444,m5,,320&_var=m5_today&r=0.7732845199699612"


分时数据:
https://web.ifzq.gtimg.cn/appstock/app/minute/query?_var=&code=sh603444&r=0.8169133625890732
https://web.ifzq.gtimg.cn/appstock/app/day/query?_var=&code=sh603444&r=0.8305712721067519
"""

class Tencent(rtbase.rtbase):
    quote_max_num = 60
    grep_stock_code = re.compile(r"(?<=_)\w+")

    @property
    def qtapi(self):
        return "http://qt.gtimg.cn/q=%s"

    @property
    def tlineapi(self):
        return 'https://web.ifzq.gtimg.cn/appstock/app/minute/query?_var=&code=%s'

    @property
    def mklineapi(self):
        return 'https://ifzq.gtimg.cn/appstock/app/kline/mkline?param=%s,m%d,,%d&_var='

    @property
    def dklineapi(self):
        return "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=&param=%s,%s,,,%d,qfq"

    def _get_headers(self):
        headers = super()._get_headers()
        return {
            **headers,
            'Referer': 'https://stockapp.finance.qq.com/'
            # https://gu.qq.com/
        }

    def get_quote_url(self, stocks):
        return self.qtapi % (','.join(stocks))

    def parse_quote(self, stock):
        def _safe_acquire_float(stock: list, idx: int) -> Optional[float]:
            """
            There are some securities that only have 50 fields. See example below:
            ['\nv_sh518801="1',
            '国泰申赎',
            '518801',
            '2.229',
            ......
            '', '0.000', '2.452', '2.006', '"']
            """
            try:
                return self._safe_price(stock[idx])
            except IndexError:
                return None

        return {
            "name": stock[1],
            "close": float(stock[3]),
            "lclose": float(stock[4]),
            "open": float(stock[5]),
            "volume": float(stock[6]) * 100,
            "bid_volume": int(stock[7]) * 100,
            "ask_volume": float(stock[8]) * 100,
            "bid1": float(stock[9]),
            "bid1_volume": int(stock[10]) * 100,
            "bid2": float(stock[11]),
            "bid2_volume": int(stock[12]) * 100,
            "bid3": float(stock[13]),
            "bid3_volume": int(stock[14]) * 100,
            "bid4": float(stock[15]),
            "bid4_volume": int(stock[16]) * 100,
            "bid5": float(stock[17]),
            "bid5_volume": int(stock[18]) * 100,
            "ask1": float(stock[19]),
            "ask1_volume": int(stock[20]) * 100,
            "ask2": float(stock[21]),
            "ask2_volume": int(stock[22]) * 100,
            "ask3": float(stock[23]),
            "ask3_volume": int(stock[24]) * 100,
            "ask4": float(stock[25]),
            "ask4_volume": int(stock[26]) * 100,
            "ask5": float(stock[27]),
            "ask5_volume": int(stock[28]) * 100,
            "最近逐笔成交": stock[29],
            "date": stock[30][0:10],
            "time": stock[30][10:], # "datetime": datetime.strptime(stock[30], "%Y%m%d%H%M%S"),
            "涨跌": float(stock[31]),
            "涨跌(%)": float(stock[32]),
            "high": float(stock[33]),
            "low": float(stock[34]),
            "价格/成交量(手)/成交额": stock[35],
            "volume": int(stock[36]) * 100,
            "amount": float(stock[37]) * 10000,
            "turnover": self._safe_price(stock[38]),
            "PE": self._safe_price(stock[39]),
            "unknown": stock[40],
            "high_2": float(stock[41]),  # 意义不明
            "low_2": float(stock[42]),  # 意义不明
            "振幅": float(stock[43]),
            "cmc": self._safe_price(stock[44]), # 流通市值
            "mc": self._safe_price(stock[45]), # 总市值
            "PB": float(stock[46]),
            "涨停价": float(stock[47]),
            "跌停价": float(stock[48]),
            "量比": self._safe_price(stock[49]),
            "委差": _safe_acquire_float(stock, 50),
            "均价": _safe_acquire_float(stock, 51),
            "市盈(动)": _safe_acquire_float(stock, 52),
            "市盈(静)": _safe_acquire_float(stock, 53),
        }

    def format_quote_response(self, rep_data):
        stocks_detail = "".join([rsp for _, rsp in rep_data])
        codes = sum([c for c,_ in rep_data], [])
        stock_details = stocks_detail.split(";")
        stock_dict = dict()
        for stock_detail in stock_details:
            stock = stock_detail.split("~")
            if len(stock) <= 49:
                continue
            s_code = self.grep_stock_code.search(stock[0]).group()
            code = s_code if s_code in codes else s_code[2:] if s_code[2:] in codes else s_code
            stock_dict[code] = self.parse_quote(stock)
        return stock_dict
    
    def get_tline_url(self, stock):
        return self.tlineapi % stock

    def format_tline_response(self, rep_data):
        return dict([[c, v['data'][c]['data']['data']] for c, v in json.loads(rep_data)])

    def get_mkline_url(self, stock, kltype=1, length=320):
        return self.mklineapi % (stock, kltype, length)

    def get_dkline_url(self, stock, kltype=101, length=320):
        if kltype == 105:
            raise NotImplementedError('not available for half year in tencent source')
        kltype = {101: 'day', 102: 'week', 103: 'month', 104: 'season', 106: 'year'}[kltype]
        return self.dklineapi % (stock, kltype, length)

    def format_mkline_response(self, rep_data):
        result = dict()
        for c, v in rep_data:
            kdata = json.loads(v)
            for k, kl in kdata['data'][c].items():
                if k.startswith('m'):
                    result[c] = [{
                        'time': f'{x[0][0:4]}-{x[0][4:6]}-{x[0][6:8]} {x[0][8:10]}:{x[0][10:]}',
                        'open': float(x[1]),
                        'close': float(x[2]),
                        'high': float(x[3]),
                        'low': float(x[4]),
                        'volume': int(float(x[5]) * 100)
                    } for x in kl]
                    break
        return result

    def format_dkline_response(self, rep_data):
        result = dict()
        for c, v in rep_data:
            kdata = json.loads(v)
            for k, kl in kdata['data'][c].items():
                if k.startswith('qfq') or k in ['day', 'week', 'month', 'season', 'year']:
                    result[c] = [{
                        'time': x[0],
                        'open': float(x[1]),
                        'close': float(x[2]),
                        'high': float(x[3]),
                        'low': float(x[4]),
                        'volume': int(float(x[5]) * 100)
                    } for x in kl]
                    break
        return result

