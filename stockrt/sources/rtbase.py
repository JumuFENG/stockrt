# coding:utf8

import abc
import logging
import requests
import importlib.util
from functools import lru_cache
if importlib.util.find_spec("numpy"):
    import numpy as np
if importlib.util.find_spec("pandas"):
    import pandas as pd
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Any, Union, List, Dict
from functools import cached_property


logger: logging.Logger = logging.getLogger('stockrt')


_DEFAULT_ARRAY_FORMAT = 'list'
def set_array_format(fmt:str):
    '''
    序列数据(tlines/klines)返回格式，默认返回纯序列，需注意各字段的含义.

    :param fmt str: 'list' | 'tuple' | 'dict' = 'json' | 'pd' | 'df' | 'np'
    :return str: 旧格式
    '''
    global _DEFAULT_ARRAY_FORMAT
    old_fmt = _DEFAULT_ARRAY_FORMAT
    _DEFAULT_ARRAY_FORMAT = fmt
    return old_fmt

def get_array_format():
    if _DEFAULT_ARRAY_FORMAT == 'np' and not importlib.util.find_spec("numpy"):
        return 'list'
    if _DEFAULT_ARRAY_FORMAT in ('pd', 'df') and not importlib.util.find_spec("pandas"):
        return 'list'
    return _DEFAULT_ARRAY_FORMAT


class rtbase(abc.ABC):
    # 每次请求的最大股票数
    quote_max_num = 800

    @staticmethod
    def get_fullcode(stock_code):
        """判断股票ID对应的证券市场
        匹配规则
        ["4", "8", "92"] 为 bj
        ['5', '6', '7', '9', '110', '113', '118', '132', '204'] 为 sh
        其余为 sz

        :param stock_code str: 股票代码, 若以 'sz', 'sh', 'bj' 开头直接返回，否则使用内置规则判断

        :return str: 以 'sz', 'sh', 'bj' 开头的股票代码
        """
        assert isinstance(stock_code, str), "stock code need str type"

        stock_code = stock_code.lower()
        if stock_code.startswith(("sh", "sz", "zz", "bj")):
            assert len(stock_code) == 8, "full stock code length should be 8"
            return stock_code

        assert len(stock_code) == 6, "stock code length should be 6"
        bj_head = ("43", "81", "83", "87", "92")
        sh_head = ("5", "6", "7", "9", "110", "113", "118", "132", "204")
        if stock_code.startswith(bj_head):
            return f"bj{stock_code}"
        elif stock_code.startswith(sh_head):
            return f"sh{stock_code}"
        return f"sz{stock_code}"

    @staticmethod
    def to_int_kltype(kltype: Union[int, str]):
        if kltype is None:
            return 101

        validkls = {
            '1': 1, '5': 5, '15': 15, '30': 30, '60': 60, '120': 120, '240': 240,
            'd': 101, 'w': 102, 'm': 103, 'q': 104, 'h': 105, 'y': 106,
            'wk': 102, 'mon': 103, 'hy': 105, 'yr': 106, 'day': 101, 'week': 102,
            'month': 103, 'quarter': 104, 'halfyear': 105, 'year': 106
            }
        if isinstance(kltype, str):
            if kltype in validkls:
                kltype = validkls[kltype]
            elif kltype.isdigit():
                kltype = int(kltype)
        if type(kltype) is not int:
            raise ValueError(f'invalid kltype: {kltype}')
        return kltype

    @staticmethod
    @lru_cache(maxsize=1)
    def get_market_stock_count():
        url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeStockCount?node=hs_a"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return int(eval(resp.text.strip()))
        except Exception as e:
            logger.error(f"get_market_stock_count error: {str(e)}")
            return 0

    @property
    @abc.abstractmethod
    def qtapi(self):
        pass

    @property
    def qt5api(self):
        return self.qtapi

    @property
    @abc.abstractmethod
    def tlineapi(self):
        pass

    @property
    @abc.abstractmethod
    def mklineapi(self):
        pass

    @property
    @abc.abstractmethod
    def dklineapi(self):
        pass

    @property
    def fklineapi(self):
        pass

    @property
    def stocklistapi(self):
        pass

    def _stock_groups(self, stocks):
        if not isinstance(stocks, (list, tuple)):
            stocks = [stocks]
        return [stocks[i:i + self.quote_max_num] for i in range(0, len(stocks), self.quote_max_num)]

    @staticmethod
    def _safe_price(s: str) -> Optional[float]:
        try:
            return float(s)
        except ValueError:
            return 0

    @abc.abstractmethod
    def quotes(self, stocks):
        pass

    @abc.abstractmethod
    def quotes5(self, stocks):
        pass

    @abc.abstractmethod
    def tlines(self, stocks):
        ''' 分时数据
        '''
        pass

    @staticmethod
    def format_array_list(
        tlines: list[list],
        cols: Optional[list[str]] = ['time', 'price', 'volume', 'amount']
    ) -> Union[list[dict], tuple[tuple], list[tuple], Any]:
        """将K线/分时数据列表转换为指定格式。

        Args:
            tlines: 输入的K线/分时数据列表，每项为 (time, price, volume, amount)。
            cols: 字段名列表，默认 ['time', 'price', 'volume', 'amount']。

        Returns:
            根据 `get_array_format()` 返回的格式转换后的数据。
        """
        if not tlines:
            return tlines  # 空数据直接返回

        fmt = get_array_format()
        supported_fmts = ['list', 'tuple', 'dict', 'json', 'pd', 'df', 'np']
        if fmt not in supported_fmts:
            raise ValueError(f"不支持的格式: {fmt}，可选: {supported_fmts}")
        if len(tlines[0]) != len(cols):
            raise ValueError(f"数据列数不匹配: 预期 {len(cols)} 列，实际 {len(tlines[0])} 列")

        if fmt == 'list':
            return tlines
        elif fmt == 'tuple':
            return tuple(tuple(tl) for tl in tlines)
        elif fmt in ('dict', 'json'):
            return [dict(zip(cols, tl)) for tl in tlines]
        elif fmt == 'pd' or fmt == 'df':
            return pd.DataFrame(tlines, columns=cols)
        elif fmt == 'np':
            return np.array(tlines)

    @abc.abstractmethod
    def mklines(self, stocks, kltype, length=320, fq=0, withqt=False):
        '''
        分钟K线数据
        '''
        pass

    @abc.abstractmethod
    def dklines(self, stocks, kltype=101, length=320, fq=1, withqt=False):
        ''' 日K线或更大周期K线数据
        '''
        pass

    def fklines(self, stocks, kltype=101, fq=0):
        ''' 获取全部K线数据
        '''
        pass

    @abc.abstractmethod
    def klines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def qklines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def stock_list(self, market: str = 'all') -> Dict[str, Any]:
        pass


class requestbase(rtbase):
    @cached_property
    def session(self):
        return requests.session()

    @property
    def count_per_page(self):
        return 100

    @abc.abstractmethod
    def get_quote_url(self, stocks):
        pass

    @abc.abstractmethod
    def get_tline_url(self, stock):
        pass

    @abc.abstractmethod
    def get_mkline_url(self, stock, kltype='1', length=320, fq=1):
        pass

    @abc.abstractmethod
    def get_dkline_url(self, stock, kltype='101', length=320, fq=1):
        pass

    def get_fkline_url(self, stock, kltype='101', fq=0):
        pass

    def get_stock_list_url(self, page: int = 1, market: str = 'all'):
        pass

    def _get_headers(self):
        return {
            "Accept-Encoding": "gzip, deflate, sdch",
            "User-Agent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:144.0) Gecko/20100101 Firefox/144.0',
            'Connection': 'keep-alive',
        }

    def _fetch_concurrently(
        self, stocks, url_func: Callable, format_func: Callable,
        convert_code: bool = True,
        url_kwargs: Optional[dict] = {}, fmt_kwargs: Optional[dict] = {}
    ):
        """并发获取数据的通用方法"""
        if not isinstance(stocks, (list, tuple)):
            stocks = [stocks]

        def fetch_single(stock):
            if convert_code:
                fcode = [self.get_fullcode(s) for s in stock] if isinstance(stock, (list, tuple)) else self.get_fullcode(stock)
            else:
                fcode = stock
            url, headers = url_func(fcode, **url_kwargs)
            try:
                if headers:
                    self.session.headers.update(headers)
                data = self.session.get(url)
                if data and data.text:
                    return [stock, data.text]
            except Exception as e:
                logger.error(f"fetch error: {url} {str(e)}")
            return None

        results = []
        try:
            if len(stocks) <= 3:
                for stock in stocks:
                    results.append(fetch_single(stock))
            else:
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = {executor.submit(fetch_single, stock): stock for stock in stocks}
                    for future in as_completed(futures, timeout=max(10, len(stocks)//5)):
                        data = future.result()
                        if data is not None:
                            results.append(data)
        except TimeoutError as e:
            logger.error(f"fetch timeout: {str(e)}")
        except Exception as e:
            logger.error(f"fetch error: {str(e)}")
        finally:
            if results:
                return format_func(results, **fmt_kwargs)

    def format_quote_response(self, rep_data):
        return dict(rep_data)

    def format_tline_response(self, rep_data):
        return dict(rep_data)

    def format_kline_response(self, rep_data, is_minute=False, withqt=False):
        return dict(rep_data)

    def format_stock_list_response(self, rep_data, market='all'):
        return rep_data

    def quotes(self, stocks):
        stocks = self._stock_groups(stocks)
        return self._fetch_concurrently(stocks, self.get_quote_url, self.format_quote_response)

    def quotes5(self, stocks):
        return self.quotes(stocks)

    def tlines(self, stocks):
        return self._fetch_concurrently(stocks, self.get_tline_url, self.format_tline_response)

    def mklines(self, stocks, kltype, length=320, fq=1, withqt=False):
        if not self.mklineapi:
            return
        kltype = self.to_int_kltype(kltype)
        return self._fetch_concurrently(stocks, self.get_mkline_url, self.format_kline_response, url_kwargs={'kltype': kltype, 'length': length, 'fq': fq}, fmt_kwargs={'is_minute': True, 'withqt': withqt})

    def dklines(self, stocks, kltype=101, length=320, fq=1, withqt=False):
        if not self.dklineapi:
            return
        kltype = self.to_int_kltype(kltype)
        return self._fetch_concurrently(stocks, self.get_dkline_url, self.format_kline_response, url_kwargs={'kltype': kltype, 'length': length, 'fq': fq}, fmt_kwargs={'is_minute': False, 'fq': fq, 'withqt': withqt})

    def fklines(self, stocks, kltype=101, fq=0):
        if not self.fklineapi:
            return
        kltype = self.to_int_kltype(kltype)
        return self._fetch_concurrently(stocks, self.get_fkline_url, self.format_kline_response, url_kwargs={'kltype': kltype, 'fq': fq}, fmt_kwargs={'is_minute': kltype < 100 or kltype % 15 == 0, 'fq': fq, 'withqt': False})

    def klines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
        kltype = self.to_int_kltype(kltype)
        if kltype in [101, 102, 103, 104, 105, 106]:
            return self.dklines(stocks, kltype=kltype, length=length, fq=fq)
        return self.mklines(stocks, kltype=kltype, length=length, fq=fq)

    def qklines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
        kltype = self.to_int_kltype(kltype)
        if kltype in [101, 102, 103, 104, 105, 106]:
            return self.dklines(stocks, kltype=kltype, length=length, fq=fq, withqt=True)
        return self.mklines(stocks, kltype=kltype, length=length, fq=fq, withqt=True)

    def stock_list(self, market: Union[str, List[str]] = 'all') -> Dict[str, Any]:
        pages = [i for i in range(1, self.get_market_stock_count() // self.count_per_page + 2)]
        if isinstance(market, str):
            return self._fetch_concurrently(pages, self.get_stock_list_url, self.format_stock_list_response, convert_code=False, url_kwargs={'market': market}, fmt_kwargs={'market': market})
        result = {}
        for mkt in market:
            result.update(self._fetch_concurrently(pages, self.get_stock_list_url, self.format_stock_list_response, convert_code=False, url_kwargs={'market': mkt}, fmt_kwargs={'market': mkt}))
        return result


class NoneSourcePy(rtbase):
    @property
    def qtapi(self):
        pass

    @property
    def tlineapi(self):
        pass

    @property
    def mklineapi(self):
        pass

    @property
    def dklineapi(self):
        pass

    def quotes(self, stocks):
        pass

    def quotes5(self, stocks):
        pass

    def tlines(self, stocks):
        pass

    def mklines(self, stocks, kltype, length=320, fq=1, withqt=False):
        pass

    def dklines(self, stocks, kltype=101, length=320, fq=1, withqt=False):
        pass

    def klines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
        pass

    def qklines(self, stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
        pass

    def stock_list(self, market: str = 'all') -> Dict[str, Any]:
        pass