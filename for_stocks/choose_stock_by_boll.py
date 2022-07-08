import os
import tushare as ts
import numpy as np
import pandas as pd
import datetime
import talib

from sqlalchemy import create_engine
from sklearn.linear_model import LinearRegression
from funcat import *
from funcat.account import Account
from funcat.context import ExecutionContext as funcat_execution_context


# 当前股价比最近m天股价最高点下跌n-1
def select_down_from_max(m, n):
    return COUNT(HHV(H, 5) / L >= n, m) >= 1


# m个交易日内股价涨停n次
def select_limit_up(m, n):
    A1 = 100 * (C - REF(C, 1)) / REF(C, 1) >= 9.9
    A2 = COUNT(A1, m)
    return A2 > n


# m天内阴线成交量不能超过阳线成交量的1.3倍
def select_vol_limited(m, n):
    up_vol = HHV(V * (C > O), m)
    down_vol = HHV(V * (C < O), m)
    print(symbol(get_current_security()), down_vol.series)
    return down_vol < up_vol * n


def select_by_volume(n):
    d = IF(O > C, V, 0)
    u = IF(O > C, 0, V)
    d_max = HHV(d, n)
    u_max = HHV(u, n)
    return d_max < u_max


# 今天成交量至少在m个交易日有n天超过scale倍
def select_buy_volumn(m, n, scale):
    now = REF(V, 0)
    for i in range(1, m, 1):
        if now > REF(V, i) * scale:
            n = n - 1

    return (n <= 0)


# n天内存在第一次高于收盘价高于5\13\21\34\55日线
def select_over_average(n):
    candidate = 0
    for i in range(n):
        ma5 = MA(C[i], 5)
        ma13 = MA(C[i], 13)
        ma21 = MA(C[i], 21)
        ma34 = MA(C[i], 34)
        ma55 = MA(C[i], 55)
        if REF(C[i], 0) < ma5 or REF(C[i], 0) < ma13 or REF(C[i], 0) < ma21 or REF(C[i], 0) < ma34 or REF(C[i], 0) < ma55:
            continue

        ret = (COUNT((C[i] > MA(C[i], 5)) & (C[i] > MA(C[i], 13)) & (C[i] > MA(C[i], 21)) & (C[i] > MA(C[i], 34)) & (C[i] > MA(C[i], 55)), n) == 1)
        # print(i, ret, candidate, get_current_date(), select_by_volume(21), COUNT(select_buy_signal(0), 34), COUNT(100 * (C[i] - REF(C[i], 1)) / REF(C[i], 1) >= 3., 55))
        if ret and select_by_volume(21) and COUNT(select_buy_signal(0), 34) >= 1 and (COUNT(100 * (C[i] - REF(C[i], 1)) / REF(C[i], 1) >= 3., 55) >= 4):
            _, peers = zig_helper(C.series[-(i+1):], 7)
            # print(i, ret, candidate, peers, get_current_date(), select_by_volume(13), COUNT(select_buy_signal(0), 15), COUNT(100 * (C[i] - REF(C[i], 1)) / REF(C[i], 1) >= 3., 55))
            if len(peers) <= 3:
                candidate = candidate + 1
                # print(candidate, get_current_date(), symbol(get_current_security()), i, ma55, peers)
                # print(C.series[-(i+1):])
        # if ret:
        #     print(get_current_date(), symbol(get_current_security()), "突破5\\13\\21\\34\\55日均线", C, ma5)

    return candidate == 1


def select_macd_cross_up():
    diff = EMA(C, 12) - EMA(C, 26)
    dea = EMA(diff, 9)
    macd = 2 * (diff - dea)

    x_train = []
    y_train = []
    for i in range(100):
        if macd[i] > 0 and macd[i + 1] < 0:
            x_train.append(i)
            y_train.append(diff[i].value)

        if len(x_train) == 3:
            break

    x_train.reverse()
    y_train.reverse()
    x_train = list(map(lambda i: -i + max(x_train), x_train))
    if len(x_train) != 3:
        return -np.nan

    model = LinearRegression()
    model.fit(np.array(x_train).reshape(-1, 1), np.array(y_train).reshape(-1, 1))
    coef = model.coef_
    return coef


# 长期均线34\55连续n天形成上升趋势
def select_long_average_up(n):
    model = LinearRegression()
    y_train = []
    for i in range(n - 1, -1, -1):
        y_train.append(MA(C[i], 34).value)
    try:
        model.fit(np.array(range(len(y_train))).reshape(-1, 1), np.array(y_train).reshape(-1, 1))
    except Exception as e:
        return False
    ma34_coef = model.coef_

    # print(ma34_coef, y_train)
    y_train = []
    for i in range(n - 1, -1, -1):
        y_train.append(MA(C[i], 55).value)
    try:
        model.fit(np.array(range(len(y_train))).reshape(-1, 1), np.array(y_train).reshape(-1, 1))
    except Exception as e:
        return False
    ma55_coef = model.coef_

    # print(ma55_coef, y_train)
    return (ma34_coef > 0.005 or ma55_coef > 0.005) and (ma34_coef + ma55_coef) > -0.1


# 计算BOLL选择踩下轨后趋势反转碰上轨，然后回踩中轨买入
def select_boll_reverse(n):
    mid = MA(C, 20).series     # 20日均线中轨
    lower = mid - 2 * talib.STDDEV(C.series, 20, 1)    # 下轨
    upper = mid + 2 * talib.STDDEV(C.series, 20, 1)    # 上轨

    cnt = 0     # 统计从最近一个上轨下来碰到中轨的次数
    t = 0       # 统计从最近一个下轨选择的次数
    lidx = 0
    uidx = 56   # 选取一个足够大的数，防止选下降趋势
    for i in range(n, 0, -1):
        idx = len(mid) - i - 1;
        if L[i] <= lower[idx]:
            lidx = i
            t = 0

        if H[i] >= upper[idx]:
            uidx = i
            if cnt != 0:
                t = t + 1
                cnt = 0

        if uidx != 56 and L[i].value < mid[idx] and H[i].value > mid[idx]:
            cnt = cnt + 1

    # print("这是第" + str(t) + "次选择")
    # print(lidx, uidx)
    # print(C[uidx].value, C[lidx].value * 1.15)

    # 踩下轨之后再碰上轨，然后在今天回踩中轨，并且上轨股价不能超过下轨30%，防止趋势反转
    return (t <= 2) and (lidx > uidx) and (L.value < mid[len(mid) - 1]) and (H.value > mid[len(mid) - 1]) and\
            (C[uidx] < C[lidx] * 1.15)


def backtest_buy(act):
    if act.position_num == 0 and len(C.series) != 0 and select_over_average(31) and select_long_average_up(5) and\
            select_down_from_max(31, 1.12) and HHV(H, 21) / C > 1.12:
        val = float(C.value)
        num = int(act.balance / val * 100) / 100.0
        print('+ {} +, buy at {}, num {}'.format(get_current_date(), C, num))
        act.buy(get_current_security(), C.value, num)
        act.update(C.value)


def backtest_sell(act):
    if act.value > act.max_value:
        act.max_value = act.value

    if act.cnt and act.position_num != 0:
        act.profit_average_time =act.profit_average_time + 1

    if C >= act.position_price * 1.07:
        print('- {} -, sell at {}, profit average time: {}, max value: {}'.format(get_current_date(), C, act.profit_average_time, act.max_value))
        act.sell(get_current_security(), C.value, act.position_num)
        act.profit_average_time = 0
        act.max_value = 0

    if len(C.series) != 0:
        act.update(C.value)


def backtest_update(act):
    if len(C.series) != 0:
        act.update(C.value)


def callback(date, order_book_id, sym):
    pro = ts.pro_api()
    df = pro.query('daily_basic', ts_code=order_book_id,
                   fields='ts_code,trade_date,turnover_rate,volume_ratio,pe,pb,circ_mv,float_share')

    count = 0
    cnt = 0
    for i in range(21):
        if df.at[i, 'turnover_rate'] <= 1:
            count = count + 1

        if df.at[i, 'turnover_rate'] >= 4.5:
            cnt = cnt + 1

    # 最近21换手率低于1%的天数大于13天，或者没有大于5%的天数直接返回
    if count > 5 or cnt == 0:
        return

    print(date, sym)


day = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d')
day0 = (datetime.datetime.now() + datetime.timedelta(days=-3)).strftime('%Y%m%d')

data_backend = funcat_execution_context.get_data_backend()
trading_dates = data_backend.get_trading_dates(day0, day)
order_book_id_list = data_backend.get_order_book_id_list()

S("000878.SZ")
T("20200615")
select_boll_reverse(31)
print(select_long_average_up(5))

select(
   lambda: select_long_average_up(5) and select_boll_reverse(31),
   start_date=trading_dates[-1],
   end_date=trading_dates[-1],
   #start_date="20200615",
   #end_date="20200615",
   callback=callback,
)
