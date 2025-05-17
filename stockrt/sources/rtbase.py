# coding:utf8

import abc
import logging
import requests
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Any


_DEFAULT_LOGGER = None

def set_default_logger(logger: logging.Logger):
    global _DEFAULT_LOGGER
    _DEFAULT_LOGGER = logger

def get_default_logger():
    if _DEFAULT_LOGGER is None:
        logger = logging.getLogger(__name__ + '.null')
        logger.addHandler(logging.NullHandler())
        set_default_logger(logger)
    return _DEFAULT_LOGGER

def get_fullcode(stock_code):
    """判断股票ID对应的证券市场
    匹配规则
    ["4", "8", "92"] 为 bj
    ['5', '6', '7', '9', '110', '113', '118', '132', '204'] 为 sh
    其余为 sz

    :param stock_code str: 股票代码, 若以 'sz', 'sh', 'bj' 开头直接返回对应类型，否则使用内置规则判断

    :return str: 以 'sz', 'sh', 'bj' 开头的股票代码
    """
    assert isinstance(stock_code, str), "stock code need str type"

    if stock_code.startswith(("sh", "sz", "zz", "bj")):
        return stock_code

    bj_head = ("4", "8", "92")
    sh_head = ("5", "6", "7", "9", "110", "113", "118", "132", "204")
    if stock_code.startswith(bj_head):
        return f"bj{stock_code}"
    elif stock_code.startswith(sh_head):
        return f"sh{stock_code}"
    return f"sz{stock_code}"

class rtbase(abc.ABC):
    # 每次请求的最大股票数
    quote_max_num = 800
    @property
    def logger(self):
        return get_default_logger()

    @property
    def session(self):
        return requests.session()
    
    @property
    @abc.abstractmethod
    def qtapi(self):
        pass

    @property
    def qt5api(self):
        return self.qtapi

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

    def _fetch_concurrently(self, stocks, url_func: Callable, format_func: Callable, **url_kwargs):
        """并发获取数据的通用方法"""
        if not isinstance(stocks, (list, tuple)):
            stocks = [stocks]

        results = []

        def fetch_single(stock):
            try:
                fcode = get_fullcode(stock) if isinstance(stock, str) else [get_fullcode(s) for s in stock]
                url = url_func(fcode, **url_kwargs)
                data = self.session.get(url, headers=self._get_headers())
                if data and data.text:
                    return [stock, data.text]
            except Exception as e:
                self.logger.error(f"处理股票数据出错: {stock} {str(e)}")
            return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_single, stock): stock for stock in stocks}
            for future in as_completed(futures):
                data = future.result()
                if data is not None:
                    results.append(data)

        return format_func(results)

    @staticmethod
    def _safe_price(s: str) -> Optional[float]:
        try:
            return float(s)
        except ValueError:
            return 0

    def format_quote_response(self, rep_data):
        return dict(rep_data)

    def format_tline_response(self, rep_data):
        return dict(rep_data)

    def format_mkline_response(self, rep_data):
        return dict(rep_data)

    def format_dkline_response(self, rep_data):
        return dict(rep_data)

    def quotes(self, stocks):
        stocks = self._stock_groups(stocks)
        return self._fetch_concurrently(stocks, self.get_quote_url, self.format_quote_response)

    def quotes5(self, stocks):
        return self.quotes(stocks)

    def tlines(self, stocks):
        ''' 分时数据
        '''
        return self._fetch_concurrently(stocks, self.get_tline_url, self.format_tline_response)

    def mklines(self, stocks, kltype, length=320):
        '''
        分钟K线数据
        '''
        return self._fetch_concurrently(stocks, self.get_mkline_url, self.format_mkline_response, kltype=kltype, length=length)

    def dklines(self, stocks, kltype=101, length=320):
        ''' 日K线或更大周期K线数据
        '''
        return self._fetch_concurrently(stocks, self.get_dkline_url, self.format_dkline_response, kltype=kltype, length=length)
