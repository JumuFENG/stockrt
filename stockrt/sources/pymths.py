# coding:utf8
'''

need to install thsdk to use this source
pip install "thsdk>=2"

'''
import importlib.util
if importlib.util.find_spec("thsdk") is None:
    from .rtbase import NoneSourcePy as SrcThs
else:
    import time
    from datetime import datetime
    from functools import lru_cache
    from typing import Any, Union, List, Dict
    from zoneinfo import ZoneInfo
    import thsdk
    from .rtbase import rtbase, logger

    _TZ = ZoneInfo('Asia/Shanghai')
    # 逐笔成交方向: thsdk 1=卖盘, 5=买盘, 其他(如盘后 17)为中性
    _BS = {1: 2, 5: 1}


    def _int2time(value):
        """thsdk 分钟线时间字段为按位打包的 YYYYMMDDHHMM"""
        year = 2000 + ((value & 133169152) >> 20) % 100
        return datetime(
            year, (value & 983040) >> 16, (value & 63488) >> 11,
            (value & 1984) >> 6, value & 63
        )


    def _parse_day(value):
        if isinstance(value, datetime):
            return value.astimezone(_TZ) if value.tzinfo else value.replace(tzinfo=_TZ)
        text = str(value).replace('-', '').replace('/', '')
        return datetime.strptime(text[:8], '%Y%m%d').replace(tzinfo=_TZ)


    def _time_at(day, value):
        if not value:
            return day.replace(hour=0, minute=0, second=0, microsecond=0)
        parts = [int(p) for p in str(value).split(':')]
        return day.replace(
            hour=parts[0], minute=parts[1] if len(parts) > 1 else 0,
            second=parts[2] if len(parts) > 2 else 0, microsecond=0
        )


    class SrcThs(rtbase):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

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
            thsdk.auth()
            return thsdk

        @property
        def thsapi(self):
            return self.ths()

        def to_ths_market(self, code):
            if len(code) == 10:
                return code[:4]

            if len(code) == 6:
                code = self.get_fullcode(code)
            if code.startswith('sh00'):
                return 'USHI'
            if code.startswith('sh6'):
                return 'USHA'
            if code.startswith('sh9'):
                return 'USHB'
            if code.startswith('sh5'):
                return 'USHJ'
            if code.startswith('sh'):
                return 'USHD'
            if code.startswith('sz399'):
                return 'USZI'
            if code.startswith(('sz00', 'sz30')):
                return 'USZA'
            if code.startswith('sz1'):
                return 'USZJ'
            if code.startswith('bj'):
                return 'USTM'
            raise NotImplementedError(f'not valid code {code}')

        def to_ths_code(self, code):
            """转换为thsdk的code"""
            if len(code) == 10:
                return code
            m = self.to_ths_market(code)
            if m == 'USHI':
                # 不清楚同花顺的指数代码规则，大部分都是USHI1Bxxxx 工业指数 USHI1B0001
                # 上证指数是USHI1A0001，还有少数1C，如USHI1C0002
                if code[-6:] == '000001':
                    return m + '1A0001'
                return m + '1B' + code[-4:]
            return m + code[-6:]

        def _quote(self, code):
            frame = self.thsapi.get_price(self.to_ths_code(code), count=2)
            if frame is None or frame.empty:
                return None
            last = frame.iloc[-1]
            lclose = frame.iloc[-2]['close'] if len(frame) > 1 else last['close']
            price = last['close']
            return {
                'name': '',
                'price': price,
                'lclose': lclose,
                'change': (price - lclose) / lclose if lclose else 0,
                'change_px': price - lclose,
                'volume': int(last['volume']),
                'amount': last['turnover'],
            }

        def quotes(self, stocks):
            if isinstance(stocks, str):
                stocks = [stocks]
            result = {}
            for c in stocks:
                try:
                    quote = self._quote(c)
                except Exception as e:
                    logger.error(f"fetch quote error: {c} {str(e)}")
                    quote = None
                if quote is not None:
                    result[c] = quote
                time.sleep(0.04)
            return result

        def quotes5(self, stocks):
            if isinstance(stocks, str):
                stocks = [stocks]
            result = self.quotes(stocks)
            stock_codes = {
                self.to_ths_code(c): c for c in result
                if self.to_ths_market(c) not in ('USZI', 'USHI')
            }
            if not stock_codes:
                return result
            try:
                books = self.thsapi.depth(list(stock_codes))
            except Exception as e:
                logger.error(f"fetch depth error: {str(e)}")
                return result
            for book in books.itertuples():
                code = stock_codes.get(book.full_code)
                if code is None:
                    continue
                side = 'bid' if book.side == 'bid' else 'ask'
                result[code][f'{side}{book.level}'] = book.price
                result[code][f'{side}{book.level}_volume'] = book.volume
            return result

        def format_tline_response(self, rep_data):
            pass

        def tlines(self, stocks):
            if isinstance(stocks, str):
                stocks = [stocks]
            result = {}
            for c in stocks:
                try:
                    frame = self.thsapi.intraday_data(self.to_ths_code(c))
                except Exception as e:
                    logger.error(f"fetch tline error: {c} {str(e)}")
                    frame = None
                if frame is not None and not frame.empty:
                    rows = []
                    prev_volume = prev_turnover = 0
                    for r in frame.itertuples():
                        t = _int2time(int(r.time))
                        volume, turnover = int(r.volume), float(r.turnover)
                        rows.append([t.strftime('%H:%M'), r.price, volume - prev_volume, turnover - prev_turnover])
                        prev_volume, prev_turnover = volume, turnover
                    result[c] = self.format_array_list(rows, ['time', 'price', 'volume', 'amount'])
                time.sleep(0.04)
            return result

        def format_kline_response(self, frame):
            rows = []
            for ts, kl in frame.iterrows():
                t = ts if hasattr(ts, 'hour') else _int2time(int(ts))
                rows.append([
                    t.strftime('%Y-%m-%d' if t.hour == 0 and t.minute == 0 else '%Y-%m-%d %H:%M'),
                    kl['open'], kl['close'], kl['high'], kl['low'], kl['volume'], kl['turnover']
                ])
            return self.format_array_list(rows, ['time', 'open', 'close', 'high', 'low', 'volume', 'amount'])

        def mklines(self, stocks, kltype, length=320, fq=1, withqt=False):
            if isinstance(stocks, str):
                stocks = [stocks]
            kltype = self.to_int_kltype(kltype)
            intervals = {
                1: '1m', 5: '5m', 15: '15m', 30: '30m', 60: '60m', 120: '120m',
                101: 'day', 102: 'week', 103: 'month', 104: 'quarter', 106: 'year'
            }
            if kltype not in intervals:
                raise ValueError(f'不支持的K线类型: {kltype}')
            interval = intervals[kltype]
            adj = ['', 'forward', 'backward'][fq]
            klines = {}
            for c in stocks:
                try:
                    frame = self.thsapi.klines(self.to_ths_code(c), interval=interval, count=length, adjust=adj)
                except Exception as e:
                    logger.error(f"fetch kline error: {c} {str(e)}")
                    frame = None
                if frame is not None and not frame.empty:
                    klines[c] = self.format_kline_response(frame)
                time.sleep(0.04)
            return klines

        def dklines(self, stocks, kltype=101, length=320, fq=1, withqt=False):
            return self.mklines(stocks, kltype, length, fq, withqt)

        def klines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
            return self.mklines(stocks, kltype, length, fq, False)

        def qklines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
            return self.mklines(stocks, kltype, length, fq, True)

        def stock_list(self, market: str = 'all'):
            if isinstance(market, (list, tuple)):
                result = {}
                for mkt in market:
                    result.update(self.stock_list(mkt))
                return result
            markets = {
                'sha': [('USHA', None)],
                'sza': [('USZA', None)],
                'bjs': [('USTM', None)],
                'kcb': [('USHA', ('688', '689'))],
                'cyb': [('USZA', ('300', '301'))],
                'all': [('USHA', None), ('USZA', None), ('USTM', None)],
            }.get(market)
            if markets is None:
                raise ValueError(f'不支持的market: {market}')
            stocks = []
            for thmarket, prefix in markets:
                start = 0
                while True:
                    frame = self.thsapi.market_securities(thmarket, start=start, count=5000)
                    if frame is None or frame.empty:
                        break
                    for r in frame.itertuples():
                        if prefix is None or r.code.startswith(prefix):
                            stocks.append({'code': r.code, 'name': r.name})
                    if len(frame) < 5000:
                        break
                    start += len(frame)
            return {market: stocks}

        def transactions(self, stocks, date=None, start=''):
            if isinstance(stocks, str):
                stocks = [stocks]
            if isinstance(start, str):
                start = [start] * len(stocks)
            result = {}
            for i, c in enumerate(stocks):
                if isinstance(start, list) and i < len(start):
                    st = start[i]
                elif isinstance(start, dict) and c in start:
                    st = start[c]
                else:
                    st = ''
                day = _parse_day(date) if date is not None else datetime.now(_TZ)
                start_time = _time_at(day, st)
                end_time = day.replace(hour=23, minute=59, second=59) if date is not None else datetime.now(_TZ)
                try:
                    ticks = self.thsapi.list_security_ticks(
                        security=self.to_ths_code(c), window={'start': start_time, 'end': end_time}
                    )
                except Exception as e:
                    logger.error(f"fetch transactions error: {c} {str(e)}")
                    continue
                rows = []
                for r in ticks.itertuples():
                    if r.time < start_time.timestamp():
                        continue
                    rows.append([
                        datetime.fromtimestamp(r.time, _TZ).strftime('%H:%M:%S'),
                        float(r.price), int(r.volume), _BS.get(int(r.deal_type), 0)
                    ])
                result[c] = self.format_array_list(rows, ['time', 'price', 'volume', 'bs'])
                time.sleep(0.04)
            return result
