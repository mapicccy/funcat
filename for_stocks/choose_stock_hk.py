import os
import time
import akshare as ak
import numpy as np
import pandas as pd
import datetime
import requests

from sklearn.linear_model import LinearRegression
from funcat import *
from funcat.account import Account
from funcat.context import ExecutionContext as funcat_execution_context


# 当前股价比最近m天股价最高点下跌n-1
def select_down_from_max(m, n):
    return COUNT(HHV(H, 5) / L >= n, m) >= 1


def select_by_volume(n):
    d = IF(O > C, V, 0)
    u = IF(O > C, 0, V)
    d_max = HHV(d, n)
    u_max = HHV(u, n)
    return d_max < u_max


# 通达信八仙过海买入指标，趋势跟随
def select_buy_signal(n):
    return ((ZIG(C[n], 6) > REF(ZIG(C[n], 6), 1) and REF(ZIG(C[n], 6), 1) <= REF(ZIG(C[n], 6), 2) <= REF(
        ZIG(C[n], 6), 3) or (
                     ZIG(C[n], 22) > REF(ZIG(C[n], 22), 1) and REF(ZIG(C[n], 22), 1) <= REF(ZIG(C[n], 22), 2) <= REF(ZIG(C[n], 22),
                                                                                                         3))))


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
        print(e, y_train)
    ma34_coef = model.coef_

    # print(ma34_coef, y_train)
    y_train = []
    for i in range(n - 1, -1, -1):
        y_train.append(MA(C[i], 55).value)
    try:
        model.fit(np.array(range(len(y_train))).reshape(-1, 1), np.array(y_train).reshape(-1, 1))
    except Exception as e:
        print(e, y_train)
    ma55_coef = model.coef_

    # print(ma55_coef, y_train)
    return ma34_coef > 0. or ma55_coef > 0.


def callback(date, order_book_id, sym):
    rw = sym + " "
    ccnt = 0
    tcnt = 0
    uup = 0
    time_tmp = ""
    # trading_dates not include today for cache issue
    # 计算7年内选股策略盈利的次数，以及最大盈利比例
    for itr, time in enumerate(trading_dates[:-7]):
        T(time)
        try:
            if select_over_average(31) and select_long_average_up(2):
                if time_tmp == "":
                    time_tmp = time
                elif int(time) - int(time_tmp) < 23:  # interval between adjacent choosing must large than 23 days
                    continue

                tcnt = tcnt + 1
                cur_price = C.value
                max_price = C.value
                max_dates = itr + 30
                if itr + 30 >= len(trading_dates):
                    max_dates = len(trading_dates)
                for it in range(itr, max_dates, 1):
                    T(trading_dates[it])
                    if C.value > max_price:
                        max_price = C.value

                # regards profit if boom 4%
                if max_price > cur_price * 1.04:
                    ccnt = ccnt + 1
                    uup = int(round((max_price - cur_price) / cur_price, 2) * 100)
        except Exception as e:
            continue

    # set trade date to the origin value.
    T(date)

    if ccnt != 0:
        rw = rw + " 2015年至今选中" + str(tcnt) + "次，准确" + str(ccnt) + "次，最高盈利" + str(uup) + "%"
    print(date, rw)

    with open('hk_daily_stock', 'a+') as fp:
        fp.write(rw + "\n")


day = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d')
day0 = (datetime.datetime.now() + datetime.timedelta(days=-3)).strftime('%Y%m%d')

set_data_backend(AkshareHKDataBackend())
data_backend = funcat_execution_context.get_data_backend()
trading_dates = data_backend.get_trading_dates("20150808", day)
order_book_id_list = data_backend.get_order_book_id_list()
print(order_book_id_list)
print(len(order_book_id_list))

with open('hk_daily_stock', 'w') as fp:
    fp.write("首次筛选（捕捉短期牛股，30日内5%以上盈利视为准确）:\n")

select(
   lambda: V.value * C.value > 100000000 and select_over_average(31) and select_long_average_up(2),
   start_date=trading_dates[-1],
   end_date=trading_dates[-1],
   callback=callback,
)
