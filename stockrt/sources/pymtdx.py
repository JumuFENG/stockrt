# coding:utf8
import importlib.util
if importlib.util.find_spec("pytdx") is None:
    from .rtbase import NoneSourcePy as SrcTdx
else:
    import os
    import time
    import json
    import random
    from concurrent.futures import ThreadPoolExecutor
    from functools import cached_property
    from typing import Callable, Any, Union, List, Dict
    from pytdx.hq import TdxHq_API
    from pytdx.config.hosts import hq_hosts
    from .rtbase import rtbase


    class SrcTdx(rtbase):
        @property
        def qtapi(self):
            return 'pyqtapi'

        @property
        def tlineapi(self):
            # TODO: return 'tlineapi'
            pass

        @property
        def mklineapi(self):
            return 'mklineapi'

        @property
        def dklineapi(self):
            return 'dklineapi'

        def to_pytdx_market(self, code):
            """转换为pytdx的market"""
            if len(code) == 6:
                code = self.get_fullcode(code)
            if len(code) == 8:
                code = code[0:2]
            market = code.lower()
            pytdx_market = {'sz': 0, 'sh': 1, 'bj': 2}
            return pytdx_market[market]

        @staticmethod
        def ping(ip, port=7709, market=2, timeout=1):
            """测试TDX服务器连通性"""
            api = TdxHq_API(multithread=False)  # 每个线程独立API实例
            success = False
            starttime = time.time()
            response = None
            try:
                with api.connect(ip, port, time_out=timeout):
                    response = api.get_security_count(market)
                    success = response is not None
            except Exception:
                pass
            endtime = time.time()
            return (success, endtime - starttime, ip, port, response)

        @staticmethod
        def search_best_tdx(n=8, max_workers=16):
            hosts = [(host[1], host[2]) for host in hq_hosts]
            file_hosts = os.path.join(os.path.dirname(__file__), 'tdx_hosts.json')
            fexists = os.path.exists(file_hosts)
            update_hosts = not fexists
            if fexists:
                with open(file_hosts, 'r') as f:
                    hosts_json = json.load(f)
                if time.time() - hosts_json['last_update'] < 3600*24*15:
                    hosts = hosts_json['hosts']
                    update_hosts = False

            pmarket = random.choice([0, 1, 2])
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(SrcTdx.ping, host[0], host[1], pmarket)
                    for host in hosts
                ]
                res = [future.result() for future in futures]

            if update_hosts:
                success_to_save = [(host, port) for (success, _, host, port, _) in res if success]
                if success_to_save:
                    hosts_json = {'hosts': success_to_save, 'last_update': time.time()}
                    with open(file_hosts, 'w') as f:
                        json.dump(hosts_json, f, indent=4)

            successful_hosts = [(result, host, port, delay) for (success, delay, host, port, result) in res if success]
            values = {}
            for response, host, port, delay in successful_hosts:
                if response:
                    values.setdefault(response, []).append((host, port, delay))

            if not values:
                return []

            # 找到最长的结果组
            longest_group = max(values.values(), key=len)
            # 按delay排序并返回前n个
            sorted_hosts = sorted(longest_group, key=lambda x: x[2])[:n]
            if n == 1:
                return sorted_hosts[0][:2]
            return [[h, p] for h, p, d in sorted_hosts]

        @cached_property
        def tdxapi(self):
            api = TdxHq_API()
            if api.connect(*self.tdxhost):
                return api

        @cached_property
        def tdxhost(self):
            return self.search_best_tdx()[0]

        def format_quote_response(self, stocks, rep_data):
            result = {}
            for q in rep_data:
                fcode = self.get_fullcode(q['code'])
                code = fcode if fcode in stocks else q['code'] if q['code'] in stocks else fcode
                result[code] = {
                    'price': q['price'],
                    'change': (q['price'] - q['last_close']) / q['last_close'],
                    'change_px': q['price'] - q['last_close'],
                    'volume': q['vol'] * 100,
                    'amount': q['amount'],
                    'high': q['high'],
                    'low': q['low'],
                    'open': q['open'],
                    'lclose': q['last_close'],
                    'bid1': q['bid1'],
                    'bid2': q['bid2'],
                    'bid3': q['bid3'],
                    'bid4': q['bid4'],
                    'bid5': q['bid5'],
                    'ask1': q['ask1'],
                    'ask2': q['ask2'],
                    'ask3': q['ask3'],
                    'ask4': q['ask4'],
                    'ask5': q['ask5'],
                    'bid1_volume': q['bid_vol1'] * 100,
                    'bid2_volume': q['bid_vol2'] * 100,
                    'bid3_volume': q['bid_vol3'] * 100,
                    'bid4_volume': q['bid_vol4'] * 100,
                    'bid5_volume': q['bid_vol5'] * 100,
                    'ask1_volume': q['ask_vol1'] * 100,
                    'ask2_volume': q['ask_vol2'] * 100,
                    'ask3_volume': q['ask_vol3'] * 100,
                    'ask4_volume': q['ask_vol4'] * 100,
                    'ask5_volume': q['ask_vol5'] * 100,
                }
            return result

        def quotes(self, stocks):
            if isinstance(stocks, str):
                stocks = [stocks]
            qt = self.tdxapi.get_security_quotes([(self.to_pytdx_market(code), code[-6:]) for code in stocks])
            return self.format_quote_response(stocks, qt)

        def quotes5(self, stocks):
            return self.quotes(stocks)

        def format_tline_response(self, rep_data):
            return self.format_array_list([[q['price'], q['vol'] * 100] for q in rep_data], ['price', 'volume'])

        def tlines(self, stocks):
            # TODO: get_history_minute_time_data 需传入日期，获取当天的分时数据的接口get_minute_time_data得到的结果有错误
            if isinstance(stocks, str):
                stocks = [stocks]

            return {c: self.format_tline_response(self.tdxapi.get_history_minute_time_data(self.to_pytdx_market(c), c[-6:], 20250530)) for c in stocks}
            # return {c: self.format_tline_response(self.tdxapi.get_minute_time_data(self.to_pytdx_market(c), c[-6:])) for c in stocks}

        def format_kline_response(self, rep_data):
            return self.format_array_list([[
                kl['datetime'], kl['open'], kl['close'], kl['high'], kl['low'], kl['vol'], kl['amount']
            ] for kl in rep_data], ['time', 'open', 'close', 'high', 'low', 'volume', 'amount'])

        def mklines(self, stocks, kltype, length=320, withqt=False):
            if isinstance(stocks, str):
                stocks = [stocks]
            kltype = self.to_int_kltype(kltype)
            categories = {5: 0, 15: 1, 30: 2, 60: 3, 101: 4, 102: 5, 103: 6, 1: 8, 104: 10, 106: 11}
            # category: K线类型（0 5分钟K线; 1 15分钟K线; 2 30分钟K线; 3 1小时K线; 4 日K线; 5 周K线; 6 月K线; 7 1分钟; 8 1分钟K线; 9 日K线; 10 季K线; 11 年K线）
            assert kltype in categories, f'不支持的K线类型: {kltype}'
            return {c : self.format_kline_response(self.tdxapi.get_security_bars(categories[kltype], self.to_pytdx_market(c), c[-6:], 0, length)) for c in stocks}

        def dklines(self, stocks, kltype=101, length=320, withqt=False):
            return self.mklines(stocks, kltype, length, withqt)

        def klines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320) -> Dict[str, Any]:
            return self.mklines(stocks, kltype, length, False)

        def qklines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320) -> Dict[str, Any]:
            return self.mklines(stocks, kltype, length, True)
