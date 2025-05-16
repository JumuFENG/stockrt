# coding:utf8
from typing import List, Dict, Any, Optional, Union
from functools import lru_cache

from .sources.rtbase import get_default_logger
from .sources.sina import Sina
from .sources.tencent import Tencent
from .sources.eastmoney import EastMoney


class FetchWrapper(object):
    def __init__(
        self,
        api_name: str,
        func_name: str,
        data_sources: List[str],
    ):
        """
        数据获取包装器

        :param api_name: 数据源API属性名
        :param func_name: 要调用的方法名
        :param data_sources: 数据源优先级列表（会复制一份避免修改外部列表）
        :param logger: 可选的日志记录器
        """
        self.api_name = api_name
        self.func_name = func_name
        self._original_sources = data_sources.copy()  # 保留原始顺序
        self._current_sources = data_sources.copy()   # 当前可用数据源
        self._failed_sources = set()                  # 完全失败的数据源

    @property
    def logger(self):
        return get_default_logger()

    @staticmethod
    def _src_unified(source):
        if source in ['sina']:
            return 'sina'
        if source in ['qq', 'tencent']:
            return 'tencent'
        if source in ['em', 'eastmoney']:
            return 'eastmoney'
        return source

    source_objects = dict()
    @classmethod
    def get_data_source(self, source_name: str) -> Optional[Any]:
        """
        Get a data source object, given a source name.

        :param source: str, a source name, one of 'sina', 'qq', 'tencent', 'em', 'eastmoney'
        :return: a data source object, one of Sina, Tencent, EastMoney
        """
        usrc = self._src_unified(source_name)
        if usrc not in self.source_objects:
            if usrc == 'sina':
                self.source_objects[usrc] = Sina()
            elif usrc == 'tencent':
                self.source_objects[usrc] = Tencent()
            elif usrc == 'eastmoney':
                self.source_objects[usrc] = EastMoney()
            else:
                raise NotImplementedError(f"not yet implemented data source: {usrc}")

        return self.source_objects.get(usrc)

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
            self._current_sources.append(source)  # 移到末尾
            self.logger.debug(f"数据源 {source} 返回空结果，已移到备用位置")

    def _try_reset_sources(self):
        """尝试重置数据源（当所有源都失败时）"""
        if not self._current_sources and self._original_sources:
            self.logger.info("尝试重置数据源")
            self._current_sources = [
                s for s in self._original_sources
                if s not in self._failed_sources
            ]


def rtsource(source):
    return FetchWrapper.get_data_source(source)


@lru_cache(maxsize=None)
def _get_wrapper(api_name: str, func_name: str, sources: tuple) -> FetchWrapper:
    return FetchWrapper(api_name, func_name, list(sources))

qwrapper = None
def quotes(stocks: Union[str, List[str]]) -> Dict[str, Any]:
    """获取行情数据"""
    wrapper = _get_wrapper('qtapi', 'quotes', ('sina', 'tencent', 'eastmoney'))
    return wrapper.fetch(stocks)

def quotes5(stocks: Union[str, List[str]]) -> Dict[str, Any]:
    wrapper = _get_wrapper('qt5api', 'quotes5', ('sina', 'tencent', 'eastmoney'))
    return wrapper.fetch(stocks)

def tlines(stocks: Union[str, List[str]]) -> Dict[str, Any]:
    wrapper = _get_wrapper('tlineapi', 'tlines', ('sina', 'tencent', 'eastmoney'))
    return wrapper.fetch(stocks)

def mklines(stocks: Union[str, List[str]], kltype=1, length=320) -> Dict[str, Any]:
    wrapper = _get_wrapper('mklineapi', 'mklines', ('eastmoney', 'sina', 'tencent'))
    return wrapper.fetch(stocks, kltype=kltype, length=length)

def dklines(stocks: Union[str, List[str]], kltype=101, length=320) -> Dict[str, Any]:
    wrapper = _get_wrapper('dklineapi', 'dklines', ('eastmoney', 'tencent', 'sina'))
    return wrapper.fetch(stocks, kltype=kltype, length=length)

def klines(stocks: Union[str, List[str]], kltype=1, length=320) -> Dict[str, Any]:
    if kltype in [101, 102, 103, 104, 105, 106]:
        return dklines(stocks, kltype=kltype, length=length)
    return mklines(stocks, kltype=kltype, length=length)

