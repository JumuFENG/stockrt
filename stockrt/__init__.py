from .sina import Sina
from .tencent import Tencent

__version__ = '0.0.1'
__author__ = 'JumuFENG'

class rtcomposer(object):
    def __init__(self):
        pass

    def quotes(self, stocks):
        pass

    def klines(self, stocks, kltype='1'):
        pass

def rtsource(source):
    if source in ['sina']:
        return Sina()
    if source in ['qq', 'tencent']:
        return Tencent()

