# coding:utf8
'''
reference: https://pytdx-docs.readthedocs.io/zh-cn/latest/pytdx_hq/


'''
import importlib.util
if importlib.util.find_spec("pytdx") is None:
    from .rtbase import NoneSourcePy as SrcTdx
else:
    import os
    import time
    import json
    import random
    import socket
    from datetime import datetime
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from functools import cached_property
    from typing import Callable, Any, Union, List, Dict
    from .rtbase import rtbase, set_array_format
    from pytdx.hq import TdxHq_API
    from pytdx.config.hosts import hq_hosts

    from pytdx.log import log as logger, logging
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    logger.propagate = True
    logger.setLevel(logging.root.level)
    logger.info("set pytdx logger propagate!")

    class ClientWrapper:
        """包装客户端，实现连接状态管理和上下文管理协议"""
        def __init__(self, host):
            self._tdx = TdxHq_API(auto_retry=True)
            self._host = host
            self._busy = False
            self._sock = None

        @property
        def is_connected(self):
            """获取当前连接状态"""
            try:
                self._sock.send(b'', socket.MSG_DONTWAIT)
                return True
            except Exception:
                return False

        @property
        def busy(self):
            """获取当前连接状态"""
            return self._busy

        def connect(self):
            """连接到服务器"""
            if self._sock and self.is_connected:
                return True

            try:
                success = self._tdx.connect(*self._host)
                if success:
                    self._sock = self._tdx.client
                return success
            except Exception as e:
                logger.debug('connect to %s failed: %s', self._host, e)
                return False

        def disconnect(self):
            """断开连接"""
            if not self._sock or not self.is_connected:
                return

            try:
                self._tdx.disconnect()
            finally:
                self._sock = None

        def __enter__(self):
            """上下文管理入口"""
            if not self.connect():
                raise ConnectionError("Failed to connect to TDX server")
            self._busy = True
            return self._tdx

        def __exit__(self, exc_type, exc_val, exc_tb):
            """上下文管理出口"""
            self._busy = False
            return False

        def __getattr__(self, name):
            """委托所有属性访问到底层客户端"""
            return getattr(self._tdx, name)


    class SrcTdx(rtbase):
        quote_max_num = 80
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
        def tdxhosts(self):
            return self.search_best_tdx()

        @cached_property
        def clients(self):
            return [ClientWrapper(h) for h in self.tdxhosts]

        def format_quote_response(self, stocks, rep_data):
            if not rep_data:
                return {}
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
                    'time': q['servertime'].split('.')[0],
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
            batches = 1
            if len(stocks) > self.quote_max_num:
                batches = len(stocks) // self.quote_max_num + 1

            wrappers = [next((c for c in self.clients if not c.busy), None)] if batches == 1 else [ c for c in self.clients if not c.busy][:batches]
            if not wrappers:
                return

            batches = len(wrappers)
            if batches == 1:
                return self._get_quotes_for_group(wrappers[0], stocks)

            batches = len(wrappers)
            gsize = len(stocks) // batches + 1
            result = {}
            with ThreadPoolExecutor(max_workers=batches) as executor:
                futures = {
                    executor.submit(
                        self._get_quotes_for_group,
                        wrappers[i],
                        stocks[i*gsize:(i+1)*gsize]
                    ): i for i in range(batches)
                }
                for future in as_completed(futures):
                    result.update(future.result())
            return result

        def _get_quotes_for_group(self, wrapper, stocks):
            result = {}
            with wrapper as client:
                for i in range(0, len(stocks), self.quote_max_num):
                    qt = client.get_security_quotes([(self.to_pytdx_market(code), code[-6:]) for code in stocks[i:i + self.quote_max_num]])
                    if qt:
                        result.update(self.format_quote_response(stocks[i:i + self.quote_max_num], qt))
            return result

        def quotes5(self, stocks):
            return self.quotes(stocks)

        def format_tline_response(self, rep_data):
            return self.format_array_list([[q['price'], q['vol'] * 100] for q in rep_data], ['price', 'volume'])

        def tlines(self, stocks):
            if isinstance(stocks, str):
                stocks = [stocks]

            today = datetime.now().strftime('%Y%m%d')
            wrappers = [c for c in self.clients if not c.busy]
            gsize = len(stocks) // len(wrappers) + 1
            result = {}
            with ThreadPoolExecutor(max_workers=len(wrappers)) as executor:
                futures = {
                    executor.submit(
                        self._get_tlines_for_group,
                        wrappers[i],
                        stocks[i*gsize:(i+1)*gsize],
                        today
                    ): i for i in range(len(wrappers))
                }
                for future in as_completed(futures):
                    result.update(future.result())

            return result

        def _get_tlines_for_group(self, wclient, stocks, date):
            """处理单个股票组的K线获取"""
            group_result = {}
            with wclient as client:  # 每个线程获取独立的client
                for code in stocks:
                    try:
                        data = client.get_history_minute_time_data(self.to_pytdx_market(code), code[-6:], date)
                        if data:
                            group_result[code] = self.format_tline_response(data)
                    except Exception as e:
                        logger.error(f"Failed to get klines for {code}: {str(e)}")
            return group_result

        def format_kline_response(self, rep_data):
            return self.format_array_list([[
                kl['datetime'], kl['open'], kl['close'], kl['high'], kl['low'], kl['vol'], kl['amount']
            ] for kl in rep_data], ['time', 'open', 'close', 'high', 'low', 'volume', 'amount'])

        def mklines(self, stocks, kltype, length=320, fq=1, withqt=False):
            if isinstance(stocks, str):
                stocks = [stocks]
            if fq != 1:
                logger.warning('pytdx不支持复权类型%s', fq)
                return {}

            kltype = self.to_int_kltype(kltype)
            categories = {5: 0, 15: 1, 30: 2, 60: 3, 101: 4, 102: 5, 103: 6, 1: 8, 104: 10, 106: 11}
            # category: K线类型（0 5分钟K线; 1 15分钟K线; 2 30分钟K线; 3 1小时K线; 4 日K线; 5 周K线; 6 月K线; 7 1分钟; 8 1分钟K线; 9 日K线; 10 季K线; 11 年K线）
            assert kltype in categories, f'不支持的K线类型: {kltype}'

            gsize = len(stocks) // len(self.tdxhosts) + 1
            result = {}
            wrappers = [c for c in self.clients if not c.busy]
            with ThreadPoolExecutor(max_workers=len(self.clients)) as executor:
                futures = {
                    executor.submit(
                        self._get_klines_for_group,
                        wrappers[i],
                        stocks[i*gsize:(i+1)*gsize],
                        categories[kltype],
                        length
                    ): i for i in range(len(wrappers))
                }

                for future in as_completed(futures):
                    result.update(future.result())
            return result

        def _get_klines_for_group(self, wclient, stocks, category, length=320, fq=1):
            """处理单个股票组的K线获取"""
            group_result = {}
            with wclient as client:  # 每个线程获取独立的client
                for code in stocks:
                    try:
                        data = client.get_security_bars(
                            category,
                            self.to_pytdx_market(code),
                            code[-6:],
                            0,
                            length
                        )
                        if data:
                            group_result[code] = self.format_kline_response(data)
                    except Exception as e:
                        logger.error(f"Failed to get klines for {code}: {str(e)}")
            return group_result

        def dklines(self, stocks, kltype=101, length=320, fq=1, withqt=False):
            return self.mklines(stocks, kltype, length, fq, withqt)

        def klines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
            return self.mklines(stocks, kltype, length, fq, False)

        def qklines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
            return self.mklines(stocks, kltype, length, fq, True)

        def stock_list(self, market = 'all'):
            pass

        def format_transaction_response(self, rep_data, start=''):
            return [
                [tr['time'], tr['price'], tr['vol'] * 100, tr['num'], tr['buyorsell']]  if 'num' in tr 
                else [tr['time'], tr['price'], tr['vol'] * 100, tr['buyorsell']] 
            for tr in rep_data if tr['time'] >= start]

        def transactions(self, stocks, date=None, start=''):
            if isinstance(stocks, str):
                stocks = [stocks]
            if isinstance(start, str):
                start = [start] * len(stocks)
            arr_start = []
            for i, c in enumerate(stocks):
                if isinstance(start, list) and i < len(start):
                    arr_start.append(start[i])
                elif isinstance(start, dict) and c in start:
                    arr_start.append(start[c])
                else:
                    arr_start.append('')

            gsize = len(stocks) // len(self.tdxhosts) + 1
            result = {}
            wrappers = [c for c in self.clients if not c.busy]
            ofmt = set_array_format('list')
            with ThreadPoolExecutor(max_workers=len(self.clients)) as executor:
                futures = {
                    executor.submit(
                        self._get_transaction_for_group,
                        wrappers[i],
                        stocks[i*gsize:(i+1)*gsize],
                        date,
                        arr_start[i*gsize:(i+1)*gsize]
                    ): i for i in range(len(wrappers))
                }

                for future in as_completed(futures):
                    result.update(future.result())
            if ofmt != 'list':
                set_array_format(ofmt)
                for k, v in result.items():
                    cols = ['time', 'price', 'volume', 'num', 'bs'] if v and len(v[0]) == 5 else ['time', 'price', 'volume', 'bs']
                    result[k] = self.format_array_list(v, cols, {'time': 'U20', 'volume': 'int64', 'num': 'int32', 'bs': 'int32'})
            return result

        def _get_transaction_for_group(self, wclient, stocks, date=None, start=''):
            """处理单个股票组的K线获取"""
            group_result = {}
            with wclient as client:  # 每个线程获取独立的client
                for code, start_hr_min in zip(stocks, start):
                    try:
                        trans = []
                        i = 0
                        r_size = None
                        if date is not None:
                            date = int(date.replace('-', ''))
                        while True:
                            if date is None:
                                data = client.get_transaction_data(self.to_pytdx_market(code), code[-6:], len(trans), r_size or 2000)
                            else:
                                data = client.get_history_transaction_data(self.to_pytdx_market(code), code[-6:], len(trans), r_size or 2000, date)
                            if not data:
                                break
                            if r_size is None:
                                r_size = len(data)
                            trans = self.format_transaction_response(data, start_hr_min) + trans
                            if data[0]['time'] < start_hr_min or len(data) < r_size:
                                break
                            i += 1
                        group_result[code] = trans
                    except Exception as e:
                        logger.error(f"Failed to get transaction for {code}: {str(e)}")
            return group_result
