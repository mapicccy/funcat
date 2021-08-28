# Funcat

Funcat 将同花顺、通达信、文华财经等的指标公式移植到了 Python 中。

Funcat 适合做股票、期货、合约、加密数字货币的量化分析与量化交易。

原作者\后端tushare接口已经不再维护，牛市以来，为方便个人对金融量化的兴趣，顾迫切建此仓库

注：回测系统需要长时间运行，回测两年的A股交易数据需要至少2GB内存（若内存不够请创建足够swap空间）

## 重磅更新计划

- 增加加密数字货币后端，创建实例时需要填入api_key\seceret_key\passphrase, [了解详情](https://www.okex.com/account/my-api)(已完成)
- 增加对[tushare pro](https://tushare.pro/register?reg=379083)接口支持，使用需要注册[获取token](https://tushare.pro/register?reg=379083)(已完成)
- 优化tushare pro数据存储方式(已完成)
- 优化DataFrame数据，降低内存占用(进行中...)
- 增加实时数据获取(已完成，实时数据来自腾讯股票接口，http://qt.gtimg.cn/q=sh601360)
- 更新个人选股策略，并使用回测系统回测（进行中...）
	- **[MACD三次金叉线性拟合趋势](https://github.com/mapicccy/funcat#macd%E4%B8%89%E6%AC%A1%E9%87%91%E5%8F%89%E7%BA%BF%E6%80%A7%E6%8B%9F%E5%90%88%E8%B6%8B%E5%8A%BF)**
	- ...
- 由于tushare pro某些数据获取频次有特殊限制，所以计划将数据整体搬移至mysql（未开始）

## 安装
```
python setup.py install
```
**注意**：talib由于兼容性问题，请选择合适的版本自行安装，推荐通过conda管理python环境和安装软件


## notebooks 教程
- [quick-start](https://github.com/mapicccy/funcat/blob/master/notebooks/funcat-tutorial.ipynb)

## API
### 行情变量

- 开盘价：`OPEN` `O`
- 收盘价：`CLOSE` `C`
- 最高价：`HIGH` `H`
- 最低价：`LOW` `L`
- 成交量：`VOLUME` `V` `VOL`

### 工具函数

- n天前的数据：`REF`
``` python
REF(C, 10)  # 10天前的收盘价
```

- 金叉判断：`CROSS`
``` python
CROSS(MA(C, 5), MA(C, 10))  # 5日均线上穿10日均线
```

- 两个序列取最小值：`MIN`
``` python
MIN(O, C)  # K线实体的最低价
```

- 两个序列取最大值：`MAX`
``` python
MAX(O, C)  # K线实体的最高价
```

- n天都满足条件：`EVERY`
``` python
EVERY(C > MA(C, 5), 10)  # 最近10天收盘价都大于5日均线
```

- n天内满足条件的天数：`COUNT`
``` python
COUNT(C > O, 10)  # 最近10天收阳线的天数
```

- n天内最大值：`HHV`
``` python
HHV(MAX(O, C), 60)  # 最近60天K线实体的最高价
```

- n天内最小值：`LLV`
``` python
LLV(MIN(O, C), 60)  # 最近60天K线实体的最低价
```

- 求和n日数据 `SUM`
``` python
SUM(C, 10)  # 求和10天的收盘价
```

- 求绝对值 `ABS`
``` python
ABS(C - O)
```

- 条件 `IF`
``` python
IF(OPEN > CLOSE, OPEN, CLOSE)
```

### 条件「和」与「或」
因为语法的问题，我们需要使用 `&` 代替 `and` 「和」，用 `|` 代替 `or` 「或」。

``` python
# 收盘价在10日均线上 且 10日均线在20日均线上
(C > MA(C, 10)) & (MA(C, 10) > MA(C, 20))

# 收阳线 或 收盘价大于昨收
(C > O) | (C > REF(C, 1))

```

### 指标

- 均线：`MA`
``` python
MA(C, 60)  # 60日均线
```

其他更多请见：[指标库](https://github.com/cedricporter/funcat/blob/master/funcat/indicators.py)


还有更多的技术指标还在实现中，欢迎提交pr一起实现。

## 自定义公式示例
[KDJ指标](http://wiki.mbalib.com/wiki/KDJ)。随机指标（KDJ）由 George C．Lane 创制。它综合了动量观念、强弱指标及移动平均线的优点，用来度量股价脱离价格正常范围的变异程度。

``` python
N, M1, M2 = 9, 3, 3

RSV = (CLOSE - LLV(LOW, N)) / (HHV(HIGH, N) - LLV(LOW, N)) * 100
K = EMA(RSV, (M1 * 2 - 1))
D = EMA(K, (M2 * 2 - 1))
J = K * 3 - D * 2

print(K, D, J)
```

[DMI指标](http://wiki.mbalib.com/wiki/DMI)。动向指数又叫移动方向指数或趋向指数。是属于趋势判断的技术性指标，其基本原理是通过分析股票价格在上升及下跌过程中供需关系的均衡点，即供需关系受价格变动之影响而发生由均衡到失衡的循环过程，从而提供对趋势判断的依据。

对于 DMI 这个指标，你会发现 TALib 算出来的结果，和同花顺等软件的结果不一样，我对比了下实现方式，发现，是因为同花顺的公式和 TALib 的计算公式不一样，对于这种情况，我们把同花顺的公式搬过来，就可以算出和同花顺一样的结果。

``` python
M1, M2 = 14, 6

TR = SUM(MAX(MAX(HIGH - LOW, ABS(HIGH - REF(CLOSE, 1))), ABS(LOW - REF(CLOSE, 1))), M1)
HD = HIGH - REF(HIGH, 1)
LD = REF(LOW, 1) - LOW

DMP = SUM(IF((HD > 0) & (HD > LD), HD, 0), M1)
DMM = SUM(IF((LD > 0) & (LD > HD), LD, 0), M1)
DI1 = DMP * 100 / TR
DI2 = DMM * 100 / TR
ADX = MA(ABS(DI2 - DI1) / (DI1 + DI2) * 100, M2)
ADXR = (ADX + REF(ADX, M2)) / 2

print(DI1, DI2, ADX, ADXR)
```

## 选股

``` python
from funcat import *


# 选出涨停股
select(
    lambda : C / C[1] - 1 >= 0.0995,
    start_date=20161231,
	end_date=20170104,
)

'''
[20170104]
20170104 000017.XSHE 000017.SZ[深中华A]
20170104 000026.XSHE 000026.SZ[飞亚达Ａ]
20170104 000045.XSHE 000045.SZ[深纺织Ａ]
20170104 000585.XSHE 000585.SZ[东北电气]
20170104 000595.XSHE 000595.SZ[宝塔实业]
20170104 000678.XSHE 000678.SZ[襄阳轴承]
...
'''


# 选出最近30天K线实体最高价最低价差7%以内，最近100天K线实体最高价最低价差大于25%，
# 最近10天，收盘价大于60日均线的天数大于3天
select(
    lambda : ((HHV(MAX(C, O), 30) / LLV(MIN(C, O), 30) - 1 < 0.07)
              & (HHV(MAX(C, O), 100) / LLV(MIN(C, O), 100) - 1 > 0.25)
              & (COUNT(C > MA(C, 60), 10) > 3)
             ),
    start_date=20161220,
)

'''
[20170104]
20170104 600512.XSHG 600512.SH[腾达建设]
[20170103]
[20161230]
20161230 000513.XSHE 000513.SZ[丽珠集团]
...
'''


# 选出最近3天每天的成交量小于20日成交量均线，最近3天最低价低于20日均线，最高价高于20日均线
# 自定义选股回调函数
def callback(date, order_book_id, symbol):
    print("Cool, 在", date, "选出", order_book_id, symbol)


select(
    lambda : (EVERY(V < MA(V, 20) / 2, 3) & EVERY(L < MA(C, 20), 3) & EVERY(H > MA(C, 20), 3)),
    start_date=20161231,
    callback=callback,
)

'''
[20170104]
Cool, 在 20170104 选出 002633.SZ 002633.XSHE[申科股份]
Cool, 在 20170104 选出 600857.SH 600857.XSHG[宁波中百]
...
'''
```

## 单股票研究
``` python
from funcat import *
from funcat.data.tushare_backend import TushareDataBackend

set_data_backend(TushareDataBackend())

# 设置目前天数为2017年1月4日
T("20170104")
# 设置关注股票为上证指数
S("000001.SH")

# 打印 Open High Low Close
>>> print(O, H, L, C)
3133.79 3160.1 3130.11 3158.79

# 当天涨幅
>>> C / C[1] - 1
0.0072929156356

# 打印60日均线
>>> MA(C, 60)
3154.78333333

# 判断收盘价是否大于60日均线
>>> C > MA(C, 60)
True

# 30日最高价
>>> HHV(H, 30)
3301.21

# 最近30日，收盘价 Close 大于60日均线的天数
>>> COUNT(C > MA(C, 60), 30)
17

# 10日均线上穿
>>> CROSS(MA(C, 10), MA(C, 20))
False
```

## 策略
本人选股结合众多筛选条件。在每个交易日14：00左右推送当日推荐股票，感兴趣可以关注本人[微信推送服务](//wxpusher.zjiecode.com/api/qrcode/JciNb6iYRbAG7eFH3omWJ2Vtw9iBPdLVnH8MYEB8EFO8s3tHd1iTXjB55GSZQL5t.jpg)

### MACD三次金叉线性拟合趋势
``` python
import numpy as np
from funcat import *
from funcat.data.tushare_backend import TushareDataBackend

from sklearn.linear_model import LinearRegression

def select_macd_cross_up():
	diff = EMA(C, 12) - EMA(C, 26)
	dea = EMA(diff, 9)
	macd = 2 * (diff - dea)

	x_train = []
	y_train = []
	# 获取最近三次MACD金叉的diff值和索引位置
	for i in range(100):
		if macd[i] > 0 and macd[i + 1] < 0:
			x_train.append(i)
			y_train.append(diff[i].value)

		if len(x_train) == 3:
			break

	if len(x_train) != 3:
		return -np.nan

	x_train.reverse()
	y_train.reverse()
	x_train = list(map(lambda i: -i + max(x_train), x_train))

	# 线性回归拟合趋势
	model = LinearRegression()
	model.fit(np.array(x_train).reshape(-1, 1), np.array(y_train).reshape(-1, 1))

	# 返回趋势线的斜率
	return model.coef_


set_data_backend(TushareDataBackend())

# 设置目前天数为2021年5月19日
T("20210519")
# 设置关注股票为300298.SZ
S("300298.SZ")

# 输出结果[[-0.03154982]]
# 表明最近2021/05/19之前3次macd金叉趋势向下
# 趋势时刻有可能发生变化，该股在2021/08/02的趋势开始向上
print(select_macd_cross_up())
```
![image](https://user-images.githubusercontent.com/11815231/128622717-a5517f26-cc3a-492e-a283-51aec4819964.png)

import tushare as ts
import time

from funcat import *

from funcat.data.tushare_backend import TushareDataBackend

set_data_backend(TushareDataBackend())
pro = ts.pro_api()
df = pro.daily_basic(ts_code='601360.SH', fields='trade_date,turnover_rate,volume_ratio,pe,pb,circ_mv,float_share')
print(df)

# 流通股数(单位： 万股)
float_share = df.at[0, 'float_share'] * 10000
print(float_share)

df = pro.top10_floatholders(ts_code='601360.SH', start_date='20210101')
print(df)

# 十大流通股东持有股数
holder10_mv = 0
for i in range(10):
    holder10_mv = holder10_mv + df.at[i, 'hold_amount']

# 排除十大股东持有股数(单位: 万股)
others_share = float_share - holder10_mv

df = pro.stk_holdernumber(ts_code='601360.SH', start_date='20160101')
print(df)

avg_share = others_share / df.at[0, 'holder_num']
print("人均持有股数：", avg_share)

S('601360.SH')
T('20210826')

print("人均持有市值：", avg_share * C.value)
