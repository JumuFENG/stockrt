# coding:utf8
import re
import ast
import time
import json
from .rtbase import requestbase

"""reference: https://www.tgb.cn/quotes/
https://www.tgb.cn/quotes/sh601162

quotes (早盘集合竞价时返回的数据为前一天的数据)
https://hq.tgb.cn/tgb/realHQList?stockCodeList=["sz002263","sz002104","sz002235","sz002579","sh601162"]
行情（其中有买卖5档）
https://hq.tgb.cn/tgb/sz002235

分时数据
https://www.tgb.cn/hq/min/sz002235
日K(不复权)
https://jshq.tgb.cn/jshq/Astock/his/sz002235_new.js?t=2025-06-280
https://jshq.tgb.cn/jshq/Astock/his/sh600030.js?t=2025-06-280
"""

class Taogb(requestbase):
    @property
    def qtapi(self):
        # 批量行情
        return 'https://hq.tgb.cn/tgb/realHQList?stockCodeList=%s'

    @property
    def qt5api(self):
        # 单只股票买卖5档
        return 'https://hq.tgb.cn/tgb/%s'

    @property
    def tlineapi(self):
        # 分时数据
        return 'https://www.tgb.cn/hq/min/%s'

    @property
    def mklineapi(self):
        pass

    @property
    def dklineapi(self):
        # 日K数据
        return 'https://jshq.tgb.cn/jshq/Astock/his/%s.js'

    def _get_headers(self):
        headers = super()._get_headers()
        return {
            **headers,
            'Referer': 'https://www.tgb.cn/'
        }

    def get_quote_url(self, stocks):
        # stocks: list of codes like ['sz002235', 'sh601162']
        stock_list_str = json.dumps([self.get_fullcode(s) for s in stocks])
        return self.qtapi % stock_list_str, self._get_headers()

    def format_quote_response(self, rep_data):
        # rep_data: list of (codes, response_text)
        result = {}
        for codes, resp in rep_data:
            data = json.loads(resp)
            for item in data.get('dto', []):
                code = item.get('code')
                fcode = item.get('fullCode')
                code = fcode if fcode in codes else code if code in codes else fcode
                result[code] = {
                    'name': item.get('name'),
                    'price': float(item.get('price', 0)),
                    'open': float(item.get('openPrice', 0)),
                    'lclose': float(item.get('closePrice', 0)),
                    'high': float(item.get('highPrice', 0)),
                    'low': float(item.get('lowPrice', 0)),
                    'volume': float(item.get('volumn', 0)),
                    'amount': float(item.get('volumnPrice', 0)),
                    'date': item.get('lastDate'),
                    'time': item.get('lastTime'),
                    'change': float(item.get('pxChangeRate', 0)) / 100,
                    'change_px': float(item.get('pxChange', 0)),
                    'top_price': float(item.get('zhangting', 0)),
                    'bottom_price': float(item.get('dieting', 0)),
                    'mc': float(item.get('totalValue', 0)) * 1e8,  # 市值
                    'cmc': float(item.get('circulationValue', 0)) * 1e8,
                    'turnover': float(item.get('turnoverRate', 0)) / 100 if item.get('turnoverRate') else 0,
                }
        return result

    def get_quote5_url(self, stock):
        # 单只股票买卖5档
        return self.qt5api % self.get_fullcode(stock), self._get_headers()

    def quotes5(self, stocks):
        return self._fetch_concurrently(stocks, self.get_quote5_url, self.format_quote5_response)

    def format_quote5_response(self, rep_data):
        result = {}
        for code, resp in rep_data:
            data = json.loads(resp)
            dto = data.get('dto')
            if not dto:
                continue
            result[code] = {
                'name': dto.get('name'),
                'code': dto.get('code'),
                'price': float(dto.get('price', 0)),
                'open': float(dto.get('openPrice', 0)),
                'lclose': float(dto.get('closePrice', 0)),
                'high': float(dto.get('highPrice', 0)),
                'low': float(dto.get('lowPrice', 0)),
                'volume': float(dto.get('volumn', 0)),
                'amount': float(dto.get('volumnPrice', 0)),
                'ask1': float(dto.get('sell_1', 0)), 'ask1_volume': int(dto.get('sell_1_s', 0)),
                'ask2': float(dto.get('sell_2', 0)), 'ask2_volume': int(dto.get('sell_2_s', 0)),
                'ask3': float(dto.get('sell_3', 0)), 'ask3_volume': int(dto.get('sell_3_s', 0)),
                'ask4': float(dto.get('sell_4', 0)), 'ask4_volume': int(dto.get('sell_4_s', 0)),
                'ask5': float(dto.get('sell_5', 0)), 'ask5_volume': int(dto.get('sell_5_s', 0)),
                'bid1': float(dto.get('buy_1', 0)), 'bid1_volume': int(dto.get('buy_1_s', 0)),
                'bid2': float(dto.get('buy_2', 0)), 'bid2_volume': int(dto.get('buy_2_s', 0)),
                'bid3': float(dto.get('buy_3', 0)), 'bid3_volume': int(dto.get('buy_3_s', 0)),
                'bid4': float(dto.get('buy_4', 0)), 'bid4_volume': int(dto.get('buy_4_s', 0)),
                'bid5': float(dto.get('buy_5', 0)), 'bid5_volume': int(dto.get('buy_5_s', 0)),
                'date': dto.get('lastDate'),
                'time': dto.get('lastTime'),
                'change': float(dto.get('pxChangeRate', 0)) / 100,
                'change_px': float(dto.get('pxChange', 0)),
            }
        return result

    def get_tline_url(self, stock):
        return self.tlineapi % stock, self._get_headers()

    def format_tline_response(self, rep_data):
        result = {}
        for c, v in rep_data:
            data = json.loads(v)
            tline = []
            dto = data.get('dto', '')
            if not dto:
                result[c] = []
                continue
            for line in dto.strip().split('\r\n'):
                parts = line.split(',')
                if len(parts) < 4:
                    continue
                tline.append([
                    parts[0],                # time
                    float(parts[1]),         # price
                    float(parts[2]),         # volume
                    float(parts[3]),         # amount
                ])
            result[c] = self.format_array_list(tline, ['time', 'price', 'volume', 'amount'])
        return result

    def get_mkline_url(self, stock, kltype='1', length=320, fq=1):
        pass

    def get_dkline_url(self, stock, kltype='d', length=320, fq=1):
        # kltype: 'd' for 日K, 'w' for 周K, 'm' for 月K
        # Only 日K supported in this example
        kltype = self.to_int_kltype(kltype)
        if kltype != 101:  # 101 is the code for 日K
            raise ValueError("Only 日K (101) is supported in TGB.")
        return self.dklineapi % self.get_fullcode(stock), self._get_headers()

    def format_kline_response(self, rep_data, is_minute=False, fq=0, **kwargs):
        result = {}
        for c, v in rep_data:
            m = re.search(r'var\s+\w+\s*=\s*(\[[^\]]*\]);', v)
            if not m:
                continue
            arr = json.loads(m.group(1))
            karr = []
            for line in arr:
                # Example: "2024-12-06,42.19,43.94,54.84,54.84,43.14,89128.0,4.394192E8"
                parts = line.split(',')
                if len(parts) < 8:
                    continue
                karr.append([
                    parts[0],                        # time
                    float(parts[2]),                 # open
                    float(parts[3]),                 # close
                    float(parts[4]),                 # high
                    float(parts[5]),                 # low
                    int(float(parts[6])*100),        # volume
                    float(parts[7]),                 # amount
                    (float(parts[3]) - float(parts[1])) / float(parts[1]) if float(parts[1]) != 0 else 0,  # change
                    float(parts[3]) - float(parts[1]),  # change_px
                ])
            result[c] = self.format_array_list(
                karr, ['time', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change', 'change_px']
            )
        return result

