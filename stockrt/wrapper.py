# coding:utf8
from .sources.sina import Sina
from .sources.tencent import Tencent


datasources = dict()

def _source_key(source):
    if source in ['sina']:
        return 'sina'
    if source in ['qq', 'tencent']:
        return 'tencent'

def rtsource(source):
    source_key = _source_key(source)
    if source_key not in datasources:
        if source_key == 'sina':
            datasources[source_key] = Sina()
        elif source_key == 'tencent':
            datasources[source_key] = Tencent()

    return datasources.get(source_key)


klsourcesm = ['sina', 'tencent']
def mklines(stocks, kltype=1, length=320):
    return _fetch(klsourcesm,  'mklineapi', 'mklines', stocks, kltype=kltype, length=length)

klsourcesd = ['tencent']
def dklines(stocks, kltype=101, length=320):
    return _fetch(klsourcesd, 'dklineapi', 'dklines', stocks, kltype=kltype, length=length)

qsources = ['sina', 'tencent']
def quotes(stocks):
    return _fetch(qsources, 'qtapi', 'quotes', stocks)

tsources = ['sina', 'tencent']
def tlines(stocks):
    return _fetch(tsources, 'tlineapi', 'tlines', stocks)


def _fetch(sources, apiname, method, *args, **kwargs):
    for s in sources:
        dsource = rtsource(s)
        if dsource and getattr(dsource, apiname) is not None:
            return getattr(dsource, method)(*args, **kwargs)

def klines(stocks, kltype=1, length=320):
    if kltype in [101, 102, 103, 104, 105, 106]:
        return dklines(stocks, kltype=kltype, length=length)
    return mklines(stocks, kltype=kltype, length=length)

