# coding:utf8
import re
import time
import json
import hashlib
from .rtbase import requestbase

"""
reference: https://www.cls.cn/quotation
https://www.cls.cn/stock?code=sh601011

财联社无法获取ETF的数据,无法获取分钟级别的K线, 可以同时获取多个股票的分时数据

实时行情
https://x-quote.cls.cn/quote/stocks/basic?app=CailianpressWeb&fields=secu_name,secu_code,trade_status,change,change_px,last_px&os=web&secu_codes=sh000001,sz399001,sh000905,sz399006,sh000300,899050.BJ&sv=7.7.5

五档买卖行情
https://x-quote.cls.cn/quote/stock/volume?app=CailianpressWeb&field=five&os=web&secu_code=sh601011&sv=8.4.6&sign=51633b814ff44ebcf98f39047de5726f

K线
https://x-quote.cls.cn/quote/stock/kline?app=CailianpressWeb&limit=50&offset=0&os=web&secu_code=sh688169&sv=7.7.5&type=fd1&sign=53d1663ea928a6bbcf026fc434f7ace0
type:
    fd1 日线, fw 周线, fm 月线, fy 年线 (前复权)
    d1 日线, w 周线, m 月线, y 年线 (不复权)
    bd1 日线, bw 周线, bm 月线, by 年线 (后复权)
分时数据:
https://x-quote.cls.cn/quote/stock/tline?app=CailianpressWeb&fields=date,minute,last_px,business_balance,business_amount,open_px,preclose_px,av_px&os=web&secu_code=sh601011&sv=8.4.6&sign=f4040f9e8baac1916153cdda5ea28e94
https://x-quote.cls.cn/quote/stock/tline_history?app=CailianpressWeb&os=web&secu_code=sh601011&sv=8.4.6&sign=36e01d1a347ffe8e65bf81f6e97dfbe3
https://x-quote.cls.cn/quote/index/tlines?app=CailianpressWeb&os=web&secu_codes=sz000001,sh601011&sv=8.4.6&sign=9ea9e14dfc9a42ffde4591784cf23044

股票列表-涨幅榜
https://www.cls.cn/allStocks
https://x-quote.cls.cn/web_quote/web_stock/stock_list?app=CailianpressWeb&market=all&os=web&page=2&rever=1&sv=8.4.6&types=last_px,change,tr,main_fund_diff,cmc,trade_status&sign=a2cd0e7449c4a2763db426a47f3edb40
无法获取开盘价最高价最低价等信息
"""


class CailianShe(requestbase):
    clsbase_param = 'app=CailianpressWeb&os=web&sv=8.4.6'
    stocklist_page_size = 30
    @property
    def qtapi(self):
        return (
            "https://x-quote.cls.cn/quote/stocks/basic?%s&fields=open_px,av_px,high_px,low_px,change,change_px,"
            "down_price,cmc,business_amount,business_balance,secu_name,secu_code,trade_status,secu_type,preclose_px,"
            "up_price,last_px,pe,ttm_pe,pb&secu_codes=%s"
        )

    @property
    def qt5api(self):
        return "https://x-quote.cls.cn/quote/stock/volume?%s&field=five&secu_code=%s"

    @property
    def tlineapi(self):
        return "https://x-quote.cls.cn/quote/index/tlines?%s&secu_codes=%s"

    @property
    def mklineapi(self):
        pass

    @property
    def dklineapi(self):
        return "https://x-quote.cls.cn/quote/stock/kline?%s&limit=%d&offset=0&secu_code=%s&type=%s%s"

    @property
    def stocklistapi(self):
        return (
            "https://x-quote.cls.cn/web_quote/web_stock/stock_list?%s&market=%s&page=%d&rever=1&types=%s"
        )

    def get_secucode(self, stock):
        fcode = self.get_fullcode(stock)
        if fcode.startswith('sh') or fcode.startswith('sz'):
            return fcode
        if fcode.startswith('bj'):
            return fcode[-6:] + '.BJ'
        raise ValueError(f"Unsupported stock code format: {stock}")

    def secu_to_fullcode(self, secu):
        if secu.startswith('sh') or secu.startswith('sz'):
            return secu
        if secu.endswith('.BJ'):
            secu = secu.replace('.BJ', '')
            return secu if secu.startswith('bj') else 'bj' + secu
        raise ValueError(f"Unsupported security code format: {secu}")

    def _get_headers(self):
        headers = super()._get_headers()
        return {
            **headers,
            'Host': 'x-quote.cls.cn',
        }

    def get_quote_url(self, stocks):
        url = self.qtapi % (self.clsbase_param, ','.join([self.get_secucode(s) for s in stocks]))
        return url, self._get_headers()

    def get_quote5_url(self, stock):
        url = self.qt5api % (self.clsbase_param, self.get_secucode(stock))
        return url, self._get_headers()

    def quotes5(self, stocks):
        return self._fetch_concurrently(stocks, self.get_quote5_url, self.format_quote5_response)

    def get_tline_url(self, stocks):
        url = self.tlineapi % (self.clsbase_param, ','.join([self.get_secucode(s) for s in stocks]))
        return url, self._get_headers()

    def tlines(self, stocks):
        stocks = self._stock_groups(stocks)
        return self._fetch_concurrently(stocks, self.get_tline_url, self.format_tline_response)

    def get_dkline_url(self, stock, kltype='1', length=320, fq=1):
        fq_map = {0: '', 1: 'f', 2: 'b'}
        kltype_map = {101: 'd1', 102: 'w', 103: 'm', 106: 'y'}
        kltype = self.to_int_kltype(kltype)
        if kltype not in kltype_map:
            raise ValueError(f"Unsupported kltype: {kltype}")
        url = self.dklineapi % (
            self.clsbase_param, length, self.get_secucode(stock), fq_map[fq], kltype_map[kltype]
        )
        return url, self._get_headers()

    def get_mkline_url(self, stock, kltype='1', length=320, fq=1):
        pass  # 财联社不支持分钟线数据

    def mklines(self, stocks, kltype='1', length=320, fq=1):
        return None

    def format_quote_response(self, rep_data):
        result = {}
        date = time.strftime('%Y-%m-%d', time.localtime())
        time_str = time.strftime('%H:%M:%S', time.localtime())
        for codes, rsp in rep_data:
            data = json.loads(rsp)['data']
            for stock in data:
                fcode = self.secu_to_fullcode(stock)
                code = fcode if fcode in codes else fcode[-6:] if fcode[-6:] in codes else fcode
                result[code] = {
                    'name': data[stock]['secu_name'],
                    'open': data[stock]['open_px'],
                    'lclose': data[stock]['preclose_px'],
                    'price': data[stock]['last_px'],
                    'high': data[stock]['high_px'],
                    'low': data[stock]['low_px'],
                    'date': date, 'time': time_str,
                    'volume': int(data[stock]['business_amount']),
                    'amount': float(data[stock]['business_balance']),
                    'change': float(data[stock]['change']),
                    'change_px': float(data[stock]['change_px']),
                    'bottom_price': float(data[stock]['down_price']),
                    'top_price': float(data[stock]['up_price']),
                    'cmc': 0 if data[stock]['cmc'] is None else float(data[stock]['cmc']),
                    'avg_price': data[stock]['av_px'],
                    'trade_status': data[stock]['trade_status'],
                    'secu_type': data[stock]['secu_type'],
                    'PE': data[stock]['pe'],
                    'TTM_PE': data[stock]['ttm_pe'],
                    'PB': data[stock]['pb'],
                }
        return result

    def format_quote5_response(self, rep_data):
        result = {}
        date = time.strftime('%Y-%m-%d', time.localtime())
        time_str = time.strftime('%H:%M:%S', time.localtime())
        for stock, rsp in rep_data:
            data = json.loads(rsp)['data']
            if data:
                result[stock] = {
                    'lclose': data['preclose_px'], 'date': date, 'time': time_str,
                    "bid1": data['b_px_1'], "bid1_volume": data['b_amount_1'] * 100,
                    "bid2": data['b_px_2'], "bid2_volume": data['b_amount_2'] * 100,
                    "bid3": data['b_px_3'], "bid3_volume": data['b_amount_3'] * 100,
                    "bid4": data['b_px_4'], "bid4_volume": data['b_amount_4'] * 100,
                    "bid5": data['b_px_5'], "bid5_volume": data['b_amount_5'] * 100,
                    "ask1": data['s_px_1'], "ask1_volume": data['s_amount_1'] * 100,
                    "ask2": data['s_px_2'], "ask2_volume": data['s_amount_2'] * 100,
                    "ask3": data['s_px_3'], "ask3_volume": data['s_amount_3'] * 100,
                    "ask4": data['s_px_4'], "ask4_volume": data['s_amount_4'] * 100,
                    "ask5": data['s_px_5'], "ask5_volume": data['s_amount_5'] * 100,
                }
        return result

    def format_tline_response(self, rep_data):
        result = {}
        for codes, rsp in rep_data:
            data = json.loads(rsp)['data']
            for stock in data:
                fcode = self.secu_to_fullcode(stock)
                code = fcode if fcode in codes else fcode[-6:] if fcode[-6:] in codes else fcode
                tline = []
                for item in data[stock]['line']:
                    tline.append([f'{str(item["minute"]//100).ljust(2, "0")}:{str(item["minute"]%100).ljust(2, "0")}', item['last_px'], item['change']])
                result[code] = self.format_array_list(tline, ['time', 'price', 'change'])
        return result

    def format_kline_response(self, rep_data, **kwargs):
        result = {}
        kcols = ['time', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'change', 'change_px']
        for code, rsp in rep_data:
            data = json.loads(rsp)['data']
            klarr = []
            for item in data:
                date = '%04d-%02d-%02d' % (item['date']//10000, item['date']%10000//100, item['date']%100)
                klarr.append([
                    date, item['open_px'], item['close_px'], item['high_px'], item['low_px'],
                    item['business_amount'], item['business_balance'],
                    item['amp'], item['change'], item['close_px'] - item['preclose_px'],
                ])
            result[code] = self.format_array_list(klarr, kcols)
        return result

    def get_signcode(self, param):
        # 将param先hash再执行md5
        hash_obj = hashlib.sha1(param.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        md5_obj = hashlib.md5(hash_hex.encode('utf-8'))
        signcode = md5_obj.hexdigest()
        return signcode

    def get_stock_list_url(self, page = 1, market = 'all'):
        types = 'last_px,change,tr,main_fund_diff,cmc,trade_status'
        market = {'all': 'all', 'sha': 'h', 'sza': 's'}.get(market, 'all')
        param = f'app=CailianpressWeb&market={market}&os=web&page={page}&rever=1&sv=8.4.6&types={types}'
        signcode = self.get_signcode(param)
        url = self.stocklistapi % (self.clsbase_param, market, page, types) + f"&sign={signcode}"
        return url, self._get_headers()

    def parse_stock_list(self, rep_data):
        data = json.loads(rep_data)['data']['data']
        return [{
            'code': stock['secu_code'],
            'name': stock['secu_name'],
            'close': stock['last_px'],
            'lclose': stock['last_px'] / (stock['change'] + 1),
            'change_px': stock['last_px'] - stock['last_px'] / (stock['change'] + 1),
            'change': stock['change'],
        } for stock in data]

    def stock_list_for_market(self, market: str = 'all'):
        pages = [self.get_market_stock_count(market) // self.stocklist_page_size + 1]
        return self._fetch_concurrently(pages, self.get_stock_list_url, self.format_stock_list_response, convert_code=False, url_kwargs={'market': market}, fmt_kwargs={'market': market})
