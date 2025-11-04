# coding:utf8
import re
import time
import json
from .rtbase import requestbase, logger

"""
reference: https://vip.stock.finance.sina.com.cn/mkt/
https://finance.sina.com.cn/realstock/company/sh600798/nc.shtml

K线
新浪的K线不可以指定复权类型, 得到的数据默认是不复权的

1: https://quotes.sina.cn/cn/api/jsonp_v2.php/x/CN_MarketDataService.getKLineData?symbol=sh601798&scale=1&ma=no&datalen=24

2: http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh600798&scale=120&ma=no&datalen=20

接口1返回的是jsonp数据，接口2返回的是json数据，接口2没有scale 1/120

分时数据:

股票列表-涨幅榜
https://vip.stock.finance.sina.com.cn/mkt/#stock_hs_up

https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeStockCount?node=hs_a
https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=4&num=40&sort=changepercent&asc=0&node=hs_a&symbol=&_s_r_a=page
https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=100&sort=changepercent&asc=0&node=hs_a&symbol=&_s_r_a=page

"""


class Sina(requestbase):
    quote_max_num = 800
    grep_detail = re.compile(
        r"(\d+)=[^\s]([^\s,]+?)%s%s"
        % (r",([\.\d]+)" * 29, r",([-\.\d:]+)" * 2)
    )
    grep_detail_with_prefix = re.compile(
        r"(\w{2}\d+)=[^\s]([^\s,]+?)%s%s"
        % (r",([\.\d]+)" * 29, r",([-\.\d:]+)" * 2)
    )
    del_null_data_stock = re.compile(
        r"(\w{2}\d+)=\"\";"
    )

    def __init__(self):
        super(Sina, self).__init__()

    @property
    def qtapi(self):
        return "http://hq.sinajs.cn/rn=%d&list=%s"

    @property
    def tlineapi(self):
        return ('https://cn.finance.sina.com.cn/minline/getMinlineData'
                '?symbol=%s&callback=&version=7.11.0&dpc=1')

    @property
    def mklineapi(self):
        return ('https://quotes.sina.cn/cn/api/jsonp_v2.php/x/CN_MarketDataService.getKLineData'
                '?symbol=%s&scale=%d&ma=no&datalen=%d')

    @property
    def dklineapi(self):
        return self.mklineapi

    @property
    def stocklistapi(self):
        return ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                "Market_Center.getHQNodeData?page=%d&num=100&sort=changepercent&asc=0&node=%s&symbol=&_s_r_a=page")

    def _get_headers(self):
        headers = super()._get_headers()
        return {
            **headers,
            'Referer': 'http://finance.sina.com.cn/'
        }

    def get_quote_url(self, stocks):
        return self.qtapi % (int(time.time() * 1000), ','.join(stocks)), self._get_headers()

    def format_quote_response(self, rep_data):
        stocks_detail = "".join([rsp for _, rsp in rep_data])
        codes = sum([c for c,_ in rep_data], [])
        stocks_detail = self.del_null_data_stock.sub('', stocks_detail)
        stocks_detail = stocks_detail.replace(' ', '')
        grep_str = self.grep_detail_with_prefix
        result = grep_str.finditer(stocks_detail)
        stock_dict = dict()
        for stock_match_object in result:
            stock = stock_match_object.groups()
            code = stock[0] if stock[0] in codes else stock[0][2:] if stock[0][2:] in codes else stock[0]
            price = float(stock[4])
            if (price == 0 or float(stock[2])) and stock[12] == stock[22]:
                # 如果价格为0，或者开盘价为0，买1价等于卖1价，是集合竞价
                price = float(stock[12])
            stock_dict[code] = dict(
                name=stock[1],
                open=float(stock[2]),
                lclose=float(stock[3]),
                price=price,
                high=float(stock[5]),
                low=float(stock[6]),
                buy=float(stock[7]),
                sell=float(stock[8]),
                volume=int(stock[9]) if int(stock[9]) * float(stock[6]) < float(stock[10]) < int(stock[9]) * float(stock[5]) else int(stock[9]) * 100,
                amount=float(stock[10]),
                change=(price - float(stock[3])) / float(stock[3]),
                change_px=price - float(stock[3]),
                bid1_volume=int(stock[11]),
                bid1=float(stock[12]),
                bid2_volume=int(stock[13]),
                bid2=float(stock[14]),
                bid3_volume=int(stock[15]),
                bid3=float(stock[16]),
                bid4_volume=int(stock[17]),
                bid4=float(stock[18]),
                bid5_volume=int(stock[19]),
                bid5=float(stock[20]),
                ask1_volume=int(stock[21]),
                ask1=float(stock[22]),
                ask2_volume=int(stock[23]),
                ask2=float(stock[24]),
                ask3_volume=int(stock[25]),
                ask3=float(stock[26]),
                ask4_volume=int(stock[27]),
                ask4=float(stock[28]),
                ask5_volume=int(stock[29]),
                ask5=float(stock[30]),
                date=stock[31],
                time=stock[32],
            )
        return stock_dict

    def get_tline_url(self, stock):
        return self.tlineapi % stock, self._get_headers()

    def format_tline_response(self, rep_data):
        result = {}
        for c, v in rep_data:
            data = json.loads(v)['result']['data']
            result[c] = self.format_array_list([
                [d['m'][:-3], float(d['p']), int(d['v']), int(d['v']) * float(d['p']), float(d['avg_p'])] for d in data],
                ['time', 'price', 'volume', 'amount', 'avg_price'])
        return result

    def get_mkline_url(self, stock, kltype='1', length=320, fq=0):
        return self.mklineapi % (stock, kltype, length), self._get_headers()

    def format_kline_response(self, rep_data, is_minute=False, **kwargs):
        result = {}
        kpattern = r'x\((\[.*?\])\);'
        for c, kltxt in rep_data:
            m = re.search(kpattern, kltxt)
            if m:
                karr = []
                for x in json.loads(m.group(1)):
                    karr.append([
                        x['day'][:-3] if is_minute and len(x['day']) > 16 else x['day'],
                        float(x['open']),
                        float(x['close']),
                        float(x['high']),
                        float(x['low']),
                        int(x['volume']),
                        float(x['amount']) if 'amount' in x else float(x['close']) * int(x['volume'])
                    ])
                result[c] = self.format_array_list(karr, ['time', 'open', 'close', 'high', 'low', 'volume', 'amount'])
        return result

    def get_dkline_url(self, stock, kltype=101, length=320, fq=0):
        if fq != 0:
            logger.error('sina kline api only support fq=0')
        klt2scale = {101: 240, 102: 1200, 103: 7200, 106: 86400}
        assert kltype in klt2scale, f'sina kline api only support {klt2scale.keys()}'
        return self.mklineapi % (stock, klt2scale[kltype], length), self._get_headers()

    def get_stock_list_url(self, page = 1, market = 'all'):
        market = {'all': 'hs_a', 'sha': 'sh_a', 'sza': 'sz_a', 'kcb': 'kcb', 'cyb': 'cyb', 'bjs': 'hs_bjs'}.get(market, 'hs_a')
        return self.stocklistapi % (page, market), self._get_headers()

    def parse_stock_list(self, rep_data):
        data = json.loads(rep_data)
        return [{
            'code': stock['symbol'],
            'name': stock['name'],
            'close': float(stock['trade']),
            'high': float(stock['high']),
            'low': float(stock['low']),
            'open': float(stock['open']),
            'lclose': float(stock['trade'] ) - float(stock['pricechange']),
            'change_px': float(stock['pricechange']),
            'change': float(stock['changepercent']) / 100,
            'volume': int(stock['volume']) * 100,
            'amount': float(stock['amount']),
        } for stock in data]

    def stock_list_for_market(self, market: str = 'all'):
        pages = [i for i in range(1, self.get_market_stock_count(market) // self.stocklist_page_size + 2)]
        return self._fetch_concurrently(pages, self.get_stock_list_url, self.format_stock_list_response, convert_code=False, url_kwargs={'market': market}, fmt_kwargs={'market': market})
