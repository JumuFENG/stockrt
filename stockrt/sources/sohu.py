# coding:utf8
import re
import ast
import time
import json
from .rtbase import requestbase

"""
reference: https://q.stock.sohu.com/
https://q.stock.sohu.com/cn/600030/index.shtml

无法获取1分钟K线, 分钟级别的数据(5,15,30,60)与其他数据不一致

https://hqm.stock.sohu.com/getqjson?code=cn_600770,cn_600030&cb=fortune_hq_cn&_=1751029644866
行情（其中有买卖5档）
https://hq.stock.sohu.com/cn/030/cn_600030-1.html?_=1751028145729
分时数据
https://hq.stock.sohu.com/cn/030/cn_600030-4.html?openinwebview_finance=false&t=1751025818086&_=1751025817806
日K
https://hq.stock.sohu.com/mkline/cn/030/cn_600030-10_2.html?_=1751025818207
周K
https://hq.stock.sohu.com/mkline/cn/030/cn_600030-11_2.html?_=1751025818221
月K
https://hq.stock.sohu.com/mkline/cn/030/cn_600030-12_2.html?_=1751025818227
5分
https://hq.stock.sohu.com/cn/030/cn_600030-9_5m.html?openinwebview_finance=false&_=1751025818233
15分
https://hq.stock.sohu.com/cn/030/cn_600030-9_15m.html?openinwebview_finance=false&_=1751025818240
资金流
https://ushq.stock.sohu.com/AFundFlow/STOCKS/600030-1.html?_=1751028140704

"""


class Sohu(requestbase):
    @property
    def qtapi(self):
        return "https://hqm.stock.sohu.com/getqjson?code=%s"

    @property
    def qt5api(self):
        return "https://hq.stock.sohu.com/cn/%s/%s-1.html"

    @property
    def tlineapi(self):
        return "https://hq.stock.sohu.com/cn/%s/%s-4.html"

    @property
    def mklineapi(self):
        # return "https://hq.stock.sohu.com/cn/%s/%s-9_%dm.html"
        pass

    @property
    def dklineapi(self):
        return "https://hq.stock.sohu.com/mkline/cn/%s/%s-%s_2.html"

    @property
    def fklineapi(self):
        return self.dklineapi

    def _get_headers(self):
        headers = super()._get_headers()
        return {
            **headers,
            'Referer': 'https://static.k.sohu.com/'
        }

    def get_cncode(self, stock):
        if len(stock) == 6 and stock.isdigit():
            return f'cn_{stock}'
        fcode = self.get_fullcode(stock)
        return f'cn_{fcode[2:]}'

    def get_quote_url(self, stocks):
        return self.qtapi % ','.join([self.get_cncode(s) for s in stocks]), self._get_headers()

    def format_quote_response(self, rep_data):
        result = {}
        for codes, resp in rep_data:
            data = json.loads(resp)
            for stock in data:
                code = stock[-6:]
                fcode = self.get_fullcode(code)
                code = fcode if fcode in codes else fcode[-6:] if fcode[-6:] in codes else fcode
                result[code] = {
                    'name': data[stock][1],
                    'price': self._safe_price(data[stock][2]),
                    'change': self._safe_price(data[stock][3].strip('%'))/100,
                    'change_px': self._safe_price(data[stock][4]),
                    'volume': int(data[stock][5])*100,
                    # int(data[stock][6])*100 分时成交量
                    'amount': int(data[stock][7])*10000,
                    'turnover': self._safe_price(data[stock][8].strip('%'))/100,
                    "量比": self._safe_price(data[stock][9]),
                    'high': self._safe_price(data[stock][10]),
                    'low': self._safe_price(data[stock][11]),
                    # data[stock][12], # 市盈率
                    'lclose': self._safe_price(data[stock][13]),
                    'open': self._safe_price(data[stock][14]),
                    # data[stock][15], # souhu.com index
                    'cmc': self._safe_price(data[stock][16])*1e8,
                    'date': data[stock][17].split(' ')[0],
                    'time': data[stock][17].split(' ')[1],
                }
        return result

    def get_quote5_url(self, stock):
        cncode = self.get_cncode(stock)
        return self.qt5api % (cncode[-3:], cncode), self._get_headers()

    def quotes5(self, stocks):
        return self._fetch_concurrently(stocks, self.get_quote5_url, self.format_quote5_response)

    def parse_jsonp(self, jsonp):
        dict_str = re.search(r'\((\[{.*}\]|\[.*\]|\{.*\})\);?$', jsonp).group(1)
        data = ast.literal_eval(dict_str)

        # 处理嵌套的字符串数组（如quote_m_r）
        # if "quote_m_r" in data:
        #     inner_str = data["quote_m_r"][1]
        #     data["quote_m_r"][1] = ast.literal_eval(f"[{inner_str}]")

        return data

    def format_quote5_response(self, rep_data):
        result = {}
        for code, resp in rep_data:
            data = self.parse_jsonp(resp)
            if not data or 'perform' not in data or not data['perform']:
                continue
            q = data['perform']
            result[code] = {
                # 'wb': self._safe_price(q[0].strip('%'))/100, # 委比
                # 'wr': q[1], # 委差
                'price': float(data['price_A1'][2]),
                'ask5': float(q[2]), 'ask5_volume': int(q[3]) * 100,
                'ask4': float(q[4]), 'ask4_volume': int(q[5]) * 100,
                'ask3': float(q[6]), 'ask3_volume': int(q[7]) * 100,
                'ask2': float(q[8]), 'ask2_volume': int(q[9]) * 100,
                'ask1': float(q[10]), 'ask1_volume': int(q[11]) * 100,
                'bid1': float(q[12]), 'bid1_volume': int(q[13]) * 100,
                'bid2': float(q[14]), 'bid2_volume': int(q[15]) * 100,
                'bid3': float(q[16]), 'bid3_volume': int(q[17]) * 100,
                'bid4': float(q[18]), 'bid4_volume': int(q[19]) * 100,
                'bid5': float(q[20]), 'bid5_volume': int(q[21]) * 100,
                # q[22],  # 外盘  q[23],  # 内盘
                'date': '-'.join(data['time'][:3]), 'time': ':'.join(data['time'][3:]),
            }
        return result

    def get_tline_url(self, stock):
        if stock.startswith(('sh00', 'sz399')):
            return None, None
        cncode = self.get_cncode(stock)
        return self.tlineapi % (cncode[-3:], cncode), self._get_headers()

    def format_tline_response(self, rep_data):
        result = {}
        for c, v in rep_data:
            data = self.parse_jsonp(v)
            if not data:
                continue
            tline = []
            for d in data[1:]:
                tline.append([d[0], float(d[1]), int(d[3])*100, float(d[4])*10000, float(d[2])])
            result[c] = self.format_array_list(tline, ['time', 'price', 'volume', 'amount', 'avg_price'])
        return result

    def get_mkline_url(self, stock, kltype='5', length=320, fq=1):
        klt = self.to_int_kltype(kltype)
        if klt not in [5, 15, 30, 60]:
            raise ValueError("Invalid period for Sohu MKLine API")
        cncode = self.get_cncode(stock)
        return self.mklineapi % (cncode[-3:], cncode, klt), self._get_headers()

    def get_dkline_url(self, stock, kltype='101', length=320, fq=1):
        klt = self.to_int_kltype(kltype)
        if klt not in [101, 102, 103]:  # 101: 日K, 102: 周K, 103: 月K
            raise ValueError("Invalid kltype for Sohu DKLine API")
        if stock.startswith(('sh00', 'sz399')):
            return None, None
        cncode = self.get_cncode(stock)
        klt -= 91
        return self.dklineapi % (cncode[-3:], cncode, klt), self._get_headers()

    def get_fkline_url(self, stock, kltype='101', fq=0):
        return self.get_dkline_url(stock, kltype, fq=fq)

    def format_mkline_response(self, rep_data, fq=0, **kwargs):
        result = {}
        for c, v in rep_data:
            data = self.parse_jsonp(v)
            if not data:
                continue
            karr = []
            for d in data:
                date = d[0][0:4] + '-' + d[0][4:6] + '-' + d[0][6:8]
                karr.append([
                    date,  # date
                    float(d[1]),  # open
                    float(d[2]),  # close
                    float(d[3]),  # high
                    float(d[4]),  # low
                    int(d[5])*100,    # volume
                    float(d[6])*10000,  # amount
                    float(d[9].strip('%')) / 100,  # change
                    float(d[8]),  # change_px
                ])
            result[c] = self.format_array_list(
                karr, ['time', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change', 'change_px']
            )

    def format_kline_response(self, rep_data, is_minute=False, fq=0, **kwargs):
        if is_minute:
            return self.format_mkline_response(rep_data, fq=fq, **kwargs)
        result = {}
        dkey = 'dataBasic' if fq == 0 else 'dataDiv'
        for c, v in rep_data:
            data = self.parse_jsonp(v)
            if not data or dkey not in data:
                continue
            karr = []
            for d in reversed(data[dkey]):
                date = d[0][0:4] + '-' + d[0][4:6] + '-' + d[0][6:8]
                karr.append([
                    date,  # date
                    float(d[1]),  # open
                    float(d[2]),  # close
                    float(d[3]),  # high
                    float(d[4]),  # low
                    int(float(d[5])*100),    # volume
                    float(d[6])*10000,  # amount
                    float(d[9].strip('%')) / 100,  # change
                    float(d[8]),  # change_px
                ])
            result[c] = self.format_array_list(
                karr, ['time', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change', 'change_px']
            )
        return result
