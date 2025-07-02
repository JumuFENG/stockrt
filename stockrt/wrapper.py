# coding:utf8
import math
import inspect
import traceback
from functools import lru_cache
from typing import List, Dict, Any, Optional, Union

from .sources.rtbase import get_default_logger, rtbase
from .sources.sina import Sina
from .sources.tencent import Tencent
from .sources.eastmoney import EastMoney
from .sources.xueqiu import Xueqiu
from .sources.cailianshe import CailianShe
from .sources.sohu import Sohu
from .sources.taogb import Taogb
from .sources.pymtdx import SrcTdx
from .sources.pymths import SrcThs


def get_fullcode(code):
    return rtbase.get_fullcode(code)

class FetchWrapper(object):
    def __init__(
        self,
        api_name: str,
        func_name: str,
        data_sources: List[str],
        parrallel: bool = False
    ):
        """
        数据获取包装器

        :param api_name: 数据源API属性名
        :param func_name: 要调用的方法名
        :param data_sources: 数据源优先级列表（会复制一份避免修改外部列表）
        :param parrallel: 是否同时使用多个数据源
        """
        self.api_name = api_name
        self.func_name = func_name
        self._original_sources = data_sources.copy()  # 保留原始顺序
        self._current_sources = data_sources.copy()   # 当前可用数据源
        self._failed_sources = set()                  # 完全失败的数据源
        self._parrallel = parrallel

    @property
    def logger(self):
        return get_default_logger()

    @staticmethod
    @lru_cache(maxsize=None)
    def _get_source(usrc: str) -> rtbase:
        if usrc == 'sina':
            return Sina()
        if usrc == 'tencent':
            return Tencent()
        if usrc == 'eastmoney':
            return EastMoney()
        if usrc == 'xueqiu':
            return Xueqiu()
        if usrc == 'cailianshe':
            return CailianShe()
        if usrc == 'sohu':
            return Sohu()
        if usrc == 'tgb':
            return Taogb()
        if usrc == 'tdx':
            return SrcTdx()
        if usrc == 'ths':
            return SrcThs()

    @classmethod
    def get_data_source(self, source: str) -> rtbase:
        """
        Get a data source object, given a source name.

        :param source: str, a source name, one of 'sina', 'qq', 'tencent', 'em', 'eastmoney', 'tdx'
        :return: a data source object, one of Sina, Tencent, EastMoney, SrcTdx
        """
        source = source.lower()
        if source in ['sina']:
            source = 'sina'
        elif source in ['qq', 'tencent']:
            source = 'tencent'
        elif source in ['em', 'eastmoney']:
            source = 'eastmoney'
        elif source in ['xq', 'xueqiu']:
            source = 'xueqiu'
        elif source in ['cls', 'cailianshe']:
            source = 'cailianshe'
        elif source in ['sohu']:
            source = 'sohu'
        elif source in ['tgb', 'taogb']:
            source = 'tgb'
        elif source in ['tdx', 'pytdx']:
            source = 'tdx'
        elif source in ['ths', 'thsdk']:
            source = 'ths'
        else:
            raise NotImplementedError(f"not yet implemented data source: {source}")

        return self._get_source(source)

    api_default_sources = {
        # api_name, sources, parrallel
        'quotes': ['qtapi', ('tencent', 'cls', 'tgb', 'ths', 'sina', 'xueqiu', 'eastmoney', 'sohu'), False],
        'quotes5': ['qt5api', ('sina', 'tencent', 'ths', 'xueqiu', 'eastmoney', 'cls', 'sohu', 'tgb'), False],
        'tlines': ['tlineapi', ('cls', 'sina', 'tencent', 'eastmoney', 'sohu', 'tgb'), False],
        'mklines': ['mklineapi', ('tencent', 'xueqiu', 'ths', 'eastmoney', 'sina'), True],
        'q_mklines': ['mklineapi', ('tencent'),  False], # 只有tencent可以同时获取quotes和kline
        'dklines': ['dklineapi', ('eastmoney', 'tdx', 'xueqiu', 'cls', 'sohu', 'ths', 'tencent'), True],
        'q_dklines': ['dklineapi', ('tencent',), False],
        'fklines': ['fklineapi', ('eastmoney', 'tdx', 'sohu', 'tgb'), True],
    }

    @staticmethod
    @lru_cache(maxsize=None)
    def get_wrapper(func_name, withQ=False):
        akey = f'q_{func_name}' if withQ else func_name
        if akey not in FetchWrapper.api_default_sources:
            raise NotImplementedError(f"not yet implemented api: {akey}")
        api_name, sources, parrallel = FetchWrapper.api_default_sources[akey]
        return FetchWrapper(api_name, func_name, list(sources), parrallel=parrallel)

    @property
    def current_source_order(self) -> List[str]:
        """获取当前数据源顺序（副本）"""
        return self._current_sources.copy()

    def fetch(
        self,
        stocks: Union[str, List[str]],
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        获取数据

        :param stocks: 单个股票代码或列表
        :return: 数据字典
        """
        if not self._current_sources:
            self._try_reset_sources()
            if not self._current_sources:
                self.logger.error("所有数据源均不可用")
                return {}

        stocks_list = [stocks] if isinstance(stocks, str) else list(stocks)

        # Handle parallel fetching when enabled and stocks list is large
        if self._parrallel and len(stocks_list) > 100 and len(self._current_sources) > 1:
            retry_count = 0
            max_retries = 3
            stocks_rem = stocks_list.copy()
            paresult = {}
            while stocks_rem and retry_count < max_retries and len(self._current_sources) > 1:
                paresult.update(self._parallel_fetch(stocks_rem, *args, **kwargs))
                stocks_rem = [s for s in stocks_rem if s not in paresult]
                if not stocks_rem:
                    return paresult
                retry_count += 1
            if retry_count >= max_retries:
                self.logger.error(
                    "未完全获取，已重试 %d 次，剩余股票: %s", retry_count, stocks_rem
                )
            return paresult

        result = {}
        remaining_sources = self._current_sources.copy()
        while remaining_sources:
            source = remaining_sources.pop(0)
            try:
                data_source = self.get_data_source(source)

                # 检查数据源是否可用
                if not data_source or not hasattr(data_source, self.api_name):
                    self._handle_unavailable_source(source)
                    continue

                fetch_func = getattr(data_source, self.func_name)
                data = fetch_func(stocks_list, *args, **kwargs)
                if not data:
                    self._handle_empty_result(source)
                    continue

                result.update(data)

                # 检查是否已获取全部所需数据
                if isinstance(stocks, str):
                    return result

                stocks_list = [s for s in stocks_list if s not in result]
                if not stocks_list:
                    return result

            except Exception as e:
                self.logger.warning(
                    "Data source %s encountered an exception: %s", source, str(e)
                )
                self._handle_empty_result(source)

        return result

    def _parallel_fetch(self, stocks_list: List[str], *args, **kwargs) -> Dict[str, Any]:
        """
        Sequential fetching implementation that processes stocks one source at a time.

        :param stocks_list: List of stock codes to fetch
        :return: Combined results from all data sources
        """
        result = {}
        num_sources = len(self._current_sources)
        chunk_size = math.ceil(len(stocks_list) / num_sources)

        # Split stocks into chunks for each data source
        chunks = [
            stocks_list[i * chunk_size:(i + 1) * chunk_size]
            for i in range(num_sources)
        ]

        for i, source in enumerate(self._current_sources):
            if i >= len(chunks) or not chunks[i]:
                continue

            try:
                data = self._fetch_from_source(source, chunks[i], *args, **kwargs)
                if data:
                    result.update(data)
            except Exception as e:
                self.logger.warning(
                    "Data source %s encountered an exception: %s", 
                    source, str(e)
                )
                self._handle_empty_result(source)

        return result

    def _fetch_from_source(self, source: str, stocks: List[str], *args, **kwargs) -> Dict[str, Any]:
        """
        Helper method to fetch data from a single source, used in parallel fetching.
        
        :param source: Data source name
        :param stocks: List of stock codes to fetch from this source
        :return: Data dictionary
        """
        try:
            data_source = self.get_data_source(source)
            if not data_source or not hasattr(data_source, self.api_name):
                self._handle_unavailable_source(source)
                return {}

            fetch_func = getattr(data_source, self.func_name)
            data = fetch_func(stocks, *args, **kwargs)
            if not data:
                self._handle_empty_result(source)
                return {}

            return data
        except Exception as e:
            self.logger.warning(
                "Data source %s encountered an exception in parallel fetch: %s", 
                source, str(e)
            )
            self.logger.warning(traceback.format_exc())
            self._handle_empty_result(source)
            return {}

    def _handle_unavailable_source(self, source: str):
        """处理不可用数据源"""
        if source in self._current_sources:
            self._current_sources.remove(source)
            self._failed_sources.add(source)
            self.logger.warning(f"数据源 {source} 不可用，已临时禁用")

    def _handle_empty_result(self, source: str):
        """处理空结果数据源"""
        if source in self._current_sources:
            self._current_sources.remove(source)
            if not self._parrallel:
                self._current_sources.append(source)  # 移到末尾
            self.logger.error(f"数据源 {source}.{self.func_name} 返回空结果，已移到备用位置")

    def _try_reset_sources(self):
        """尝试重置数据源（当所有源都失败时）"""
        if not self._current_sources and self._original_sources:
            self.logger.info("尝试重置数据源")
            self._current_sources = [
                s for s in self._original_sources
                if s not in self._failed_sources
            ]


def rtsource(source: str) -> rtbase:
    '''
    获取数据源对象

    Args:
        source (str): 数据源名称
    '''
    return FetchWrapper.get_data_source(source)


def set_default_sources(key, func_name, sources, parrallel=False):
    '''
    设置默认数据源

    Args:
        key (str): key, 必须设置为func_name 或 'q_{func_name}'
        func_name (str): 方法名 'quotes', 'quotes5', 'tlines', 'mklines', 'dklines' 之一
        sources (list): 想要设置的数据源列表
        parrallel (bool, optional): 是否多个数据源同时运行.
            - False(默认): 设置的数据源会单独按顺序使用，如果前面的数据源请求失败则将其移到最后
            - True: 设置的所有数据源会同时启动，如果数据源请求失败则会移出列表，全部数据源失效才会重新启用,
                这种情况通常用于单个数据源有访问频率/总量限制的情况，
                大部分数据源只能一次获取一支股票的K线数据，平均分到多个数据源进行请求也可以提高效率
    '''
    FetchWrapper.api_default_sources[key] = (func_name, sources, parrallel)

def quotes(stocks: Union[str, List[str]]) -> Dict[str, Any]:
    """获取行情数据, 根据数据源不同, 有的带有5档买卖信息数据, 有的不带. 可以获取指数的行情数据

    Args:
        stocks (Union[str, List[str]]): 股票代码或代码列表, 股票代码可以是6位纯数字代码或者带前缀的代码(sh/sz/bj + code),
            获取指数行情数据需传入前缀，如 sh000001 为上证指数, 而000001则默认为股票即:sz000001平安银行

    Returns:
        - Dict[str, Any]: 行情数据
    """
    wrapper = FetchWrapper.get_wrapper(inspect.currentframe().f_code.co_name)
    return wrapper.fetch(stocks)

def quotes5(stocks: Union[str, List[str]]) -> Dict[str, Any]:
    '''获取带有5档买卖信息的行情数据, 根据数据源不同, 有的一次只能请求一只股票. 对于指数不建议使用该接口

    Args:
        stocks (Union[str, List[str]]): 股票代码或代码列表, 股票代码可以是6位纯数字代码或者带前缀的代码(sh/sz/bj + code)

    Returns:
        - Dict[str, Any]: 带有5档买卖信息的行情数据
    '''
    wrapper = FetchWrapper.get_wrapper(inspect.currentframe().f_code.co_name)
    return wrapper.fetch(stocks)

def tlines(stocks: Union[str, List[str]]) -> Dict[str, Any]:
    '''获取分时线数据, 可以获取指数的分时数据

    Args:
        stocks (Union[str, List[str]]): 股票代码或代码列表, 股票代码可以是6位纯数字代码或者带前缀的代码(sh/sz/bj + code),
            获取指数分时数据需传入前缀，如 sh000001 为上证指数，而000001则默认为股票即sz000001平安银行

    Returns:
        - Dict[str, Any]: 分时线数据
    '''
    wrapper = FetchWrapper.get_wrapper(inspect.currentframe().f_code.co_name)
    return wrapper.fetch(stocks)

def mklines(stocks: Union[str, List[str]], kltype=1, length=320, fq=1, withqt=False) -> Dict[str, Any]:
    wrapper = FetchWrapper.get_wrapper(inspect.currentframe().f_code.co_name, withqt)
    return wrapper.fetch(stocks, kltype=kltype, length=length, fq=fq, withqt=withqt)

def dklines(stocks: Union[str, List[str]], kltype=101, length=320, fq=1, withqt=False) -> Dict[str, Any]:
    wrapper = FetchWrapper.get_wrapper(inspect.currentframe().f_code.co_name, withqt)
    return wrapper.fetch(stocks, kltype=kltype, length=length, fq=fq, withqt=withqt)

def fklines(stocks: Union[str, List[str]], kltype: Union[int,str]=101, fq=0) -> Dict[str, Any]:
    ''' 获取全部K线数据, 一般用在日线及更大的周期，小的周期不保证能获取完整数据

    Returns:
        - Dict[str, Any]: {code1: [], code2: [] ...}
    '''
    wrapper = FetchWrapper.get_wrapper(inspect.currentframe().f_code.co_name)
    return wrapper.fetch(stocks, kltype=kltype, fq=fq)

def klines(stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
    ''' 获取K线数据, 可以获取指数的K线数据

    Args:
        stocks (Union[str, List[str]]): 股票代码或代码列表, 股票代码可以是6位纯数字代码或者带前缀的代码(sh/sz/bj + code),
            获取指数K线数据需传入前缀, 如: sh000001 为上证指数, 而000001则默认为股票即sz000001平安银行
        kltype (Union[int,str], optional): K线类型. Defaults to 1.
            - 1,5,15,30,60,120,240: 对应分钟数的K线数据
            - 101/d/day: 日K线数据
            - 102/w/wk/week: 周K线数据
            - 103/m/mon/month: 月K线数据
            - 104/q/quarter: 季度K线数据
            - 105/h/hy/hyear: 半年K线数据
            - 106/y/yr/year: 年K线数据
        length (int, optional): K线数据长度. Defaults to 320.
        fq (int, optional): 是否复权. 
            - 0: 不复权 
            - 1: 前复权 Default.
            - 2: 后复权  

    Returns:
        - Dict[str, Any]: {code1: [], code2: [] ...}
    '''
    kltype = rtbase.to_int_kltype(kltype)
    if kltype in [101, 102, 103, 104, 105, 106]:
        return dklines(stocks, kltype=kltype, length=length, fq=fq)
    return mklines(stocks, kltype=kltype, length=length, fq=fq)

def qklines(stocks: Union[str, List[str]], kltype: Union[int,str]=1, length=320, fq=1) -> Dict[str, Any]:
    ''' 获取带有行情信息的K线数据, 有的数据源获取K线数据时会同时返回行情数据, 如果没有同时返回行情数据，
    即使调用该接口也不会包含行情数据, 参数与klines一样, 返回值格式有区别

    Returns:
        - Dict[str, Any]: {code1: {'klines': [], 'qt': []}, code2: {'klines': [], 'qt': []} ...}
    '''
    kltype = rtbase.to_int_kltype(kltype)
    if kltype in [101, 102, 103, 104, 105, 106]:
        return dklines(stocks, kltype=kltype, length=length, fq=fq, withqt=True)
    return mklines(stocks, kltype=kltype, length=length, fq=fq, withqt=True)

