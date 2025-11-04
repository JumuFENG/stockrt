# coding:utf8
import time
import json
from datetime import datetime
from functools import lru_cache
from .rtbase import requestbase

"""
reference: https://xueqiu.com/hq
https://xueqiu.com/S/SH600759

https://github.com/uname-yang/pysnowball
token问题: https://github.com/uname-yang/pysnowball/issues/1

实时行情(无涨跌停价)
https://stock.xueqiu.com/v5/stock/batch/quote.json?symbol=SH000001,SZ399001,SZ399006,SH000688
https://stock.xueqiu.com/v5/stock/quote.json?symbol=SH600792
五档买卖行情
https://stock.xueqiu.com/v5/stock/realtime/pankou.json?symbol=SH600759

K线
https://stock.xueqiu.com/v5/stock/chart/kline.json?symbol=SH600759&begin=1749989758853&period=day&type=before&count=-284&indicator=kline,pe,pb,ps,pcf,market_capital,agt,ggt,balance


分时数据:
https://stock.xueqiu.com/v5/stock/chart/minute.json?symbol=SH000001&period=1d
https://stock.xueqiu.com/v5/stock/chart/minute.json?symbol=SH600759&period=5d

股票列表-涨幅榜
https://xueqiu.com/hq/detail?type=sha&order=desc&orderBy=percent&market=CN&first_name=0&second_name=3
https://stock.xueqiu.com/v5/stock/screener/quote/list.json?page=1&size=30&order=desc&order_by=percent&market=CN&type=sha
无法获取开盘价最高价最低价等信息, 总共只有5000条数据尽管A股已经不止5000只股票
"""


class Xueqiu(requestbase):
    @property
    def qtapi(self):
        return "https://stock.xueqiu.com/v5/stock/batch/quote.json?symbol=%s"

    @property
    def qt5api(self):
        return "https://stock.xueqiu.com/v5/stock/realtime/pankou.json?symbol=%s"

    @property
    def tlineapi(self):
        return 'https://stock.xueqiu.com/v5/stock/chart/minute.json?symbol=%s&period=1d'

    @property
    def mklineapi(self):
        return ('https://stock.xueqiu.com/v5/stock/chart/kline.json?'
        'symbol=%s&begin=%d&period=%s&type=%s&count=-%d'
        '&indicator=kline')
    # &indicator=kline,pe,pb,ps,pcf,market_capital,agt,ggt,balance

    @property
    def dklineapi(self):
        return self.mklineapi

    @property
    def stocklistapi(self):
        return "https://stock.xueqiu.com/v5/stock/screener/quote/list.json?page=%d&size=%d&order=desc&order_by=percent&market=CN&type=%s"

    @lru_cache(maxsize=1)
    def xueqiu_cookie(self):
        self.session.get('https://xueqiu.com/hq', headers=super()._get_headers())
        # return f'xq_a_token={r.cookies.get("xq_a_token")};u={r.cookies.get("u")};'

    def _get_headers(self):
        headers = super()._get_headers()
        self.xueqiu_cookie()
        return {
            **headers,
            'Host': 'stock.xueqiu.com',
            'Accept': 'application/json'
        }

    def get_quote_url(self, stocks):
        return self.qtapi % (','.join([self.get_fullcode(s).upper() for s in stocks])), self._get_headers()

    def format_quote_response(self, rep_data):
        stock_dict = dict()
        codes = sum([c for c,_ in rep_data], [])
        items = sum([json.loads(v)['data']['items'] for _,v in rep_data], [])
        for item in items:
            q = item['quote']
            qcode = q['symbol'].lower()
            code = qcode if qcode in codes else q['code'] if q['code'] in codes else qcode
            qdt = datetime.fromtimestamp(q['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            qdate, qtime = qdt.split()
            stock_dict[code] = {
                'name': q['name'],
                'price': q['current'],
                'date': qdate, 'time': qtime,
                'change': q['percent'] / 100,
                'change_px': q['chg'],
                'lclose': q['last_close'],
                'volume': q['volume'],
                'amount': q['amount'],
                'turnover': q['turnover_rate'] / 100 if q['turnover_rate'] else 0,
                'avg_price': q['avg_price'],
                'open': q['open'],
                'high': q['high'],
                'low': q['low'],
            }
        return stock_dict

    def get_quote5_url(self, stock):
        return self.qt5api % self.get_fullcode(stock).upper(), self._get_headers()

    def quotes5(self, stocks):
        return self._fetch_concurrently(stocks, self.get_quote5_url, self.format_quote5_response)

    def format_quote5_response(self, rep_data):
        stock_dict = dict()
        for code, rsp in rep_data:
            q = json.loads(rsp)['data']
            if not q:
                continue
            qdt = datetime.fromtimestamp(q['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            qdate, qtime = qdt.split()
            stock_dict[code] = {
                'price': q['current'], 'date': qdate, 'time': qtime,
                'bid1': q['bp1'], 'ask1': q['sp1'], 'bid1_volume': q['bc1'], 'ask1_volume': q['sc1'],
                'bid2': q['bp2'], 'ask2': q['sp2'], 'bid2_volume': q['bc2'], 'ask2_volume': q['sc2'],
                'bid3': q['bp3'], 'ask3': q['sp3'], 'bid3_volume': q['bc3'], 'ask3_volume': q['sc3'],
                'bid4': q['bp4'], 'ask4': q['sp4'], 'bid4_volume': q['bc4'], 'ask4_volume': q['sc4'],
                'bid5': q['bp5'], 'ask5': q['sp5'], 'bid5_volume': q['bc5'], 'ask5_volume': q['sc5'],
            }
        return stock_dict

    def get_tline_url(self, stock):
        return self.tlineapi % self.get_fullcode(stock).upper(), self._get_headers()

    def format_tline_response(self, rep_data):
        result = {}
        for c, v in rep_data:
            data = json.loads(v)['data']['items']
            tldata = [[datetime.fromtimestamp(d['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M'), d['current'], d['volume'], d['amount'], d['avg_price']] for d in data]
            for mt in ('09:30', '13:00'):
                idmt = next(i for i, d in enumerate(tldata) if d[0].endswith(mt))
                if idmt >= 0 and idmt + 1 < len(tldata):
                    tldata[idmt+1][2] += tldata[idmt][2]
                    tldata[idmt+1][3] += tldata[idmt][3]
                    tldata.pop(idmt)
            result[c] = self.format_array_list(tldata, ['time', 'price', 'volume', 'amount', 'avg_price'])
        return result

    def get_mkline_url(self, stock, kltype='1', length=320, fq=0):
        fqs = {0: 'normal', 1: 'before', 2: 'after'}
        return self.mklineapi % (self.get_fullcode(stock).upper(), int(time.time()*1000), f'{kltype}m', fqs[fq], length), self._get_headers()

    def format_kline_response(self, rep_data, **kwargs):
        result = {}
        for code, rsp in rep_data:
            data = json.loads(rsp)['data']
            if 'item' not in data or len(data['item']) == 0:
                continue
            cols = {c: i for i, c in enumerate(data['column'])}
            items = data['item']
            karr = []
            for x in items:
                t = datetime.fromtimestamp(x[cols['timestamp']] / 1000).strftime('%Y-%m-%d %H:%M')
                karr.append([
                    t.split()[0] if t.endswith('00:00') else t,
                    x[cols['open']],
                    x[cols['close']],
                    x[cols['high']],
                    x[cols['low']],
                    x[cols['volume']],
                    x[cols['amount']],
                    x[cols['percent']] / 100,
                    x[cols['chg']],
                    x[cols['turnoverrate']] / 100
                ])
            result[code] = self.format_array_list(
                karr, ['time', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change', 'change_px', 'turnover']
            )
        return result

    def get_dkline_url(self, stock, kltype='101', length=320, fq=1):
        kltype = self.to_int_kltype(kltype)
        if kltype < 100 or kltype % 15 == 0:
            return self.get_mkline_url(stock, kltype, length)
        period = {
            101: 'day', 102: 'week', 103: 'month', 104: 'quarter', 106: 'year'
        }
        fqs = {0: 'normal', 1: 'before', 2: 'after'}
        return self.dklineapi % (self.get_fullcode(stock).upper(), int(time.time()*1000), period[kltype], fqs[fq], length), self._get_headers()

    def get_stock_list_url(self, page = 1, market = 'all'):
        market = {'all': '', 'sha': 'sha', 'kcb': 'kcb', 'sza': 'sza', 'cyb': 'cyb'}.get(market, '')
        return self.stocklistapi % (page, self.stocklist_page_size, market), self._get_headers()

    def get_total_count(self, rep_data):
        data = json.loads(rep_data)['data']
        return data['count'], len(data['list'])

    def parse_stock_list(self, rep_data):
        data = json.loads(rep_data)['data']['list']
        return [{
            'code': stock['symbol'].lower(),
            'name': stock['name'],
            'close': stock['current'],
            'lclose': stock['current'] - stock['chg'],
            'change_px': stock['chg'],
            'change': stock['percent'] / 100,
            'volume': stock['volume'],
            'amount': stock['amount'],
        } for stock in data]
