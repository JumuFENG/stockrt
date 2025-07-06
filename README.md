### stockrt
实时获取免费股票行情, K线数据, 分时数据，目前支持新浪 / 腾讯 / 东财, 

主要目的是简化盘中需要频繁获取的情况，对几个数据源进行了统一化接口，对每一类接口都设置了数据源列表，如果某个数据源不可用则会切换到下一个数据源，并将不可用的数据源移到最后。

由于各种数据源返回的数据项不完全一致，比如行情信息有的数据源可以同时获取行情和买卖5档信息，有的需要分别获取. 有的行情信息会返回涨跌停价格而有的不会，所以在使用中建议缓存并更新数据而不是覆盖信息。如果明确需要的信息只有特定的数据源有建议先指定数据源获取一次（一般不同的数据线都是类似涨跌停价格，市值这些不太敏感的非实时信息）.

### Requirements
本项目只依赖 requests，使用了ThreadPoolExecutor， 应该3.8以上的python都支持，开发是用的python 3.11

### 安装

目前没有发布到pip， 下载源码或whl文件然后安装

```python
pip install .
or
pip install stockrt-x.x.x.-py3-none-any.whl
```

### 用法

1. 指定数据源
``` py
from stockrt import rtsource, set_logger
set_logger(...) # Optional
src_em = rtsource('em')

klines = src_em.klines('600610', 101, 100)
klines = src_em.klines(['600610', 'sh000001'], 'wk', 100)
klines = src_em.klines(['600610', '688755'], 1, 100)
klines = src_em.klines('600610', 15, 100)

src_sina = rtsource('sina')
quotes = src_sina.quotes('600610')
quotes = src_sina.quotes(['600610', 'sz003003'])

...
```

2.自动选择数据源, 默认的数据源设置的顺序，程序会自动选择顺序靠前的数据源，如果不可用会将其放到最后。

``` py
import stockrt as asrt
asrt.set_logger(...) # Optional
klines = asrt.klines('600610', 101, 100)
klines = asrt.klines(['600610', 'sh000001'], 'wk', 100)
klines = asrt.klines(['600610', '688755'], 1, 100)
klines = asrt.klines('600610', 15, 100)

quotes = asrt.quotes('600610')
quotes = asrt.quotes(['600610', 'sz003003'])

...
```


### 贡献
欢迎对本项目进行贡献！欢迎提交 PR。


### 感谢
本项目新浪/腾讯行情参考了[easyquotation](https://github.com/shidenggui/easyquotation), 
