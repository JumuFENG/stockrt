# coding:utf8
import re
import time
import json
from . import rtbase

"""
reference: https://finance.sina.com.cn/realstock/company/sh600798/nc.shtml

K线

1: https://quotes.sina.cn/cn/api/jsonp_v2.php/x/CN_MarketDataService.getKLineData?symbol=sh601798&scale=1&ma=no&datalen=24

2: http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh600798&scale=120&ma=no&datalen=20

接口1返回的是jsonp数据，接口2返回的是json数据，接口2没有scale 1/120

分时数据:
"""


class Sina(rtbase.rtbase):
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

    def _get_headers(self):
        headers = super()._get_headers()
        return {
            **headers,
            'Referer': 'http://finance.sina.com.cn/'
        }

    def get_quote_url(self, stocks):
        return self.qtapi % (int(time.time() * 1000), ','.join(stocks))

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
            stock_dict[code] = dict(
                name=stock[1],
                open=float(stock[2]),
                lclose=float(stock[3]),
                close=float(stock[4]),
                high=float(stock[5]),
                low=float(stock[6]),
                buy=float(stock[7]),
                sell=float(stock[8]),
                turnover=int(stock[9]),
                volume=float(stock[10]),
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
        return self.tlineapi % stock

    def format_tline_response(self, rep_data):
        return dict([[c, v['result']['data']] for c,v in json.loads(rep_data)])

    def get_mkline_url(self, stock, kltype='1', length=320):
        return self.mklineapi % (stock, kltype, length)

    def format_mkline_response(self, rep_data):
        result = {}
        kpattern = r'x\((\[.*?\])\);'
        for c, kltxt in rep_data:
            m = re.search(kpattern, kltxt)
            if m:
                result[c] = json.loads(m.group(1))
        return result

    def get_dkline_url(self, stock, kltype=101, length=320):
        klt2scale = {101: 240, 102: 1200, 103: 7200, 106: 86400}
        assert kltype in klt2scale, f'sina kline api only support {klt2scale.keys()}'
        return self.mklineapi % (stock, klt2scale[kltype], length)

    def format_dkline_response(self, rep_data):
        return self.format_mkline_response(rep_data)
