# coding:utf8

import abc
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


class rtbase(object):
    # 每次请求的最大股票数
    quote_max_num = 800
    @property
    def session(self):
        return requests.session()
    
    @property
    @abc.abstractmethod
    def qtapi(self):
        pass

    @abc.abstractmethod
    def get_quote_url(self, stocks):
        pass

    @property
    @abc.abstractmethod
    def tlineapi(self):
        pass

    @abc.abstractmethod
    def get_tline_url(self, stock):
        pass

    @property
    @abc.abstractmethod
    def mklineapi(self):
        pass

    @abc.abstractmethod
    def get_mkline_url(self, stock, kltype='1', length=320):
        pass

    @property
    @abc.abstractmethod
    def dklineapi(self):
        pass

    @abc.abstractmethod
    def get_dkline_url(self, stock, kltype='101', length=320):
        pass

    def _get_headers(self):
        return {
            "Accept-Encoding": "gzip, deflate, sdch",
            "User-Agent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:138.0) Gecko/20100101 Firefox/138.0',
        }

    def _stock_groups(self, stocks):
        if not isinstance(stocks, (list, tuple)):
            stocks = [stocks]
        return [stocks[i:i + self.quote_max_num] for i in range(0, len(stocks), self.quote_max_num)]

    def quotes(self, stocks):
        stocks = self._stock_groups(stocks)
        qturls = [self.get_quote_url(stock) for stock in stocks]
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.session.get, url, headers=self._get_headers()): url for url in qturls}
            for future in as_completed(futures):
                try:
                    data = future.result()
                    if data and data.text:
                        results.append(data.text)
                except Exception as e:
                    print(f"处理股票数据出错: {str(e)}")
        return self.format_quote_response(results)
    
    def format_quote_response(self, rep_data):
        pass

    def tlines(self, stocks):
        ''' 分时数据
        '''
        if not isinstance(stocks, (list, tuple)):
            stocks = [stocks]

        results = []
        def fetch_tline(stock):
            try:
                data = self.session.get(self.get_tline_url(stock), headers=self._get_headers())
                if data and data.text:
                    return [stock, data.json()]
            except Exception as e:
                print(f"处理股票数据出错: {stock} {str(e)}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_tline, stock): stock for stock in stocks}
            for future in as_completed(futures):
                data = future.result()
                if data is not None:
                    results.append(data)
        return self.format_tline_response(results)

    def format_tline_response(self, rep_data):
        return dict(rep_data)

    def klines(self, stocks, kltype='1', length=320) -> dict:
        """
        Fetches K-line data for the specified stocks.

        :param stocks list/str: A single stock symbol or a list of stock symbols for which K-line data is to be fetched.
        :param kltype str: The type of K-line data to fetch. Defaults to '1'.

            1: 1-minute K-line data
            5: 5-minute K-line data
            15: 15-minute K-line data
            30: 30-minute K-line data
            60: 1-hour K-line data
            120: 2-hour K-line data
            240: 4-hour K-line data
            101/d/day: 1-day K-line data
            102/w/wk/week: 1-week K-line data
            103/m/mon/month: 1-month K-line data
            104/q/quarter: 1-quarter K-line data
            105/h/hy/hyear: half-year K-line data
            106/y/yr/year: 1-year K-line data
        :param length int: The number of K-lines to fetch. Defaults to 320.

        :return dict: The formatted K-line dictionary.
        """
        validkls = {
            '1': 1, '5': 5, '15': 15, '30': 30, '60': 60, '120': 120, '240': 240,
            'd': 101, 'w': 102, 'm': 103, 'q': 104, 'h': 105, 'y': 106,
            'wk': 102, 'mon': 103, 'hy': 105, 'yr': 106, 'day': 101, 'week': 102,
            'month': 103, 'quarter': 104, 'halfyear': 105, 'year': 106
            }
        if isinstance(kltype, str) and kltype in validkls:
            kltype = validkls[kltype]
        elif not isinstance(kltype, int):
            raise ValueError(f"Invalid kltype: {kltype}")

        if int(kltype) < 15 or int(kltype) % 15 == 0:
            return self.mklines(stocks, kltype, length)

        return self.dklines(stocks, kltype, length)

    def mklines(self, stocks, kltype, length=320):
        '''
        分钟K线数据
        '''
        if not isinstance(stocks, (list, tuple)):
            stocks = [stocks]

        results = []
        def fetch_mkline(stock):
            try:
                data = self.session.get(self.get_mkline_url(stock, kltype, length), headers=self._get_headers())
                if data and data.text:
                    return [stock, data.text]
            except Exception as e:
                print(f"处理股票数据出错: {stock} {str(e)}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_mkline, stock): stock for stock in stocks}
            for future in as_completed(futures):
                data = future.result()
                if data is not None:
                    results.append(data)
        return self.format_mkline_response(results)

    def format_mkline_response(self, rep_data):
        return dict(rep_data)

    def dklines(self, stocks, kltype='101', length=320):
        ''' 日K线或更大周期K线数据
        '''
        if not isinstance(stocks, (list, tuple)):
            stocks = [stocks]

        results = []
        def fetch_kline(stock):
            try:
                data = self.session.get(self.get_dkline_url(stock, kltype, length), headers=self._get_headers())
                if data and data.text:
                    return [stock, data.text]
            except Exception as e:
                print(f"处理股票数据出错: {stock} {str(e)}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_kline, stock): stock for stock in stocks}
            for future in as_completed(futures):
                data = future.result()
                if data is not None:
                    results.append(data)
        return self.format_dkline_response(results)

    def format_dkline_response(self, rep_data):
        return dict(rep_data)
