# coding:utf8
'''

need to install thsdk to use this source
pip install thsdk

not support for MAC arm64
'''
import importlib.util
if importlib.util.find_spec("thsdk") is None:
    from .rtbase import NoneSourcePy as SrcThs
else:
    import time
    from functools import lru_cache
    from typing import Any, Union, List, Dict
    from thsdk import THS, Interval, Adjust
    from thsdk._constants_ import *
    from .rtbase import rtbase

    class SrcThs(rtbase):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def __del__(self):
            self.ths().disconnect()

        @property
        def qtapi(self):
            return 'pyqtapi'

        @property
        def tlineapi(self):
            pass

        @property
        def mklineapi(self):
            return 'mklineapi'

        @property
        def dklineapi(self):
            return 'dklineapi'

        @lru_cache(maxsize=1)
        def ths(self):
            return THS()

        @property
        def thsapi(self):
            ths = self.ths()
            if not ths._login:
                ths.connect()
            return ths

        def to_ths_market(self, code):
            if len(code) == 10:
                return code[:4]

            if len(code) == 6:
                code = self.get_fullcode(code)
            if code.startswith('sh00'):
                return MarketUSHI
            if code.startswith('sh6'):
                return MarketUSHA
            if code.startswith('sh9'):
                return MarketUSHB
            if code.startswith('sh5'):
                return MarketUSHJ
            if code.startswith('sh'):
                return MarketUSHD
            if code.startswith('sz399'):
                return MarketUSZI
            if code.startswith(('sz00', 'sz30')):
                return MarketUSZA
            if code.startswith('sz1'):
                return MarketUSZJ
            if code.startswith('bj'):
                return MarketUSTM
            raise NotImplementedError(f'not valid code {code}')

        def to_ths_code(self, code):
            """转换为thsdk的code"""
            if len(code) == 10:
                return code
            m = self.to_ths_market(code)
            if m == MarketUSHI:
                # 不清楚同花顺的指数代码规则，大部分都是USHI1Bxxxx 工业指数 USHI1B0001
                # 上证指数是USHI1A0001，还有少数1C，如USHI1C0002
                if code[-6:] == '000001':
                    return m + '1A0001'
                return m + '1B' + code[-4:]
            return m + code[-6:]

        def format_quote_response(self, stocks, rep_data):
            if not rep_data:
                return {}

            result = {}
            for q in rep_data:
                scode = q['代码'][-6:]
                fcode = self.get_fullcode(scode)
                if scode.startswith(('1A','1B','1C')):
                    fcode = 'sh00' + scode[-4:]
                code = fcode if fcode in stocks else scode if scode in stocks else fcode
                result[code] = {
                    'name': q['名称'],
                    'price': q['价格'],
                    'lclose': q['昨收价'],
                    'change': q['涨幅'] / 100,
                    'change_px': q['涨跌'],
                    'volume': q['成交量'],
                    'amount': q['总金额'],
                }
                if '涨停价' in q:
                    result[code]["top_price"] = q['涨停价']
                if '跌停价' in q:
                    result[code]["bottom_price"] = q['跌停价']
                if '买5价' in q:
                    result[code].update({
                        'bid1': q['买1价'],
                        'bid1_volume': q['买1量'],
                        'ask1': q['卖1价'],
                        'ask1_volume': q['卖1量'],
                        'bid2': q['买2价'],
                        'bid2_volume': q['买2量'],
                        'ask2': q['卖2价'],
                        'ask2_volume': q['卖2量'],
                        'bid3': q['买3价'],
                        'bid3_volume': q['买3量'],
                        'ask3': q['卖3价'],
                        'ask3_volume': q['卖3量'],
                        'bid4': q['买4价'],
                        'bid4_volume': q['买4量'],
                        'ask4': q['卖4价'],
                        'ask4_volume': q['卖4量'],
                        'bid5': q['买5价'],
                        'bid5_volume': q['买5量'],
                        'ask5': q['卖5价'],
                        'ask5_volume': q['卖5量'],
                    })
            return result

        def query_quote_data(self, stocks, datatypes):
            if isinstance(stocks, str):
                stocks = [stocks]
            stock_grp = {}
            for c in stocks:
                thcode = self.to_ths_code(c)
                m = thcode[:4]
                if m not in stock_grp:
                    stock_grp[m] = []
                stock_grp[m].append(thcode[-6:])

            result = {}
            for i, m in enumerate(stock_grp):
                stypes = datatypes
                if m in (MarketUSZI, MarketUSHI):
                    stypes = [s for s in stypes if s not in [69, 70]]
                stypes = ','.join([str(t) for t in stypes])
                params = {
                    'id': 200, 'codelist': ','.join(stock_grp[m]),
                    'market': m,
                    'datatype': stypes,
                    'service': 'zhu' if m in (MarketUSHA, MarketUSZA) else 'fu'}
                r = self.thsapi.query_data(params)
                result = {**result, **self.format_quote_response(stocks, r.payload.result)}
                if i < len(stock_grp) - 1:
                    time.sleep(0.03)
            return result

        def quotes(self, stocks):
            datatypes = [5,55,6,10,13,19,69,70,199112,264648]
            return self.query_quote_data(stocks, datatypes)

        def quotes5(self, stocks):
            datatypes = [5,55,6,10,13,19,69,70,199112,264648,24,25,26,27,28,29,30,31,32,33,34,35,150,151,152,153,154,155,156,157]
            return self.query_quote_data(stocks, datatypes)

        def format_tline_response(self, rep_data):
            pass

        def tlines(self, stocks):
            pass

        def format_kline_response(self, rep_data):
            result = rep_data.payload.result
            return self.format_array_list([[
                kl['时间'].strftime('%Y-%m-%d' if kl['时间'].hour == 0 and kl['时间'].minute == 0 else '%Y-%m-%d %H:%M'), kl['开盘价'], kl['收盘价'], kl['最高价'], kl['最低价'], kl['成交量'], kl['总金额']
            ] for kl in result], ['time', 'open', 'close', 'high', 'low', 'volume', 'amount'])

        def mklines(self, stocks, kltype, length=320, fq=1, withqt=False):
            if isinstance(stocks, str):
                stocks = [stocks]
            kltype = self.to_int_kltype(kltype)
            intervals = {
                1: Interval.MIN_1, 5: Interval.MIN_5, 15: Interval.MIN_15,
                30: Interval.MIN_30, 60: Interval.MIN_60, 120: Interval.MIN_120,
                101: Interval.DAY, 102: Interval.WEEK, 103: Interval.MONTH,
                104: Interval.QUARTER, 106: Interval.YEAR
            }
            assert kltype in intervals, f'不支持的K线类型: {kltype}'
            adj = [Adjust.NONE, Adjust.FORWARD, Adjust.BACKWARD][fq]
            return {c : self.format_kline_response(self.thsapi.klines(self.to_ths_code(c), interval=intervals[kltype], count=length, adjust=adj)) for c in stocks}

        def dklines(self, stocks, kltype=101, length=320, fq=1, withqt=False):
            return self.mklines(stocks, kltype, length, fq, withqt)

        def klines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
            return self.mklines(stocks, kltype, length, fq, False)

        def qklines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
            return self.mklines(stocks, kltype, length, fq, True)
