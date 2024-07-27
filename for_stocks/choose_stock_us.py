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

from wxpusher import WxPusher as wx


uid = ['UID_4yb8qx3oxePh1ZHCvFpVxNGDRAuf',
        'UID_6tyjJDIh80gYNw43z6sTkmMhsJWV',
        'UID_IeWryrp8jf3ZxGkgATIBCb4tgpzL', # qiyu
        'UID_x1ArbpSoVqdcRr8EHTJYPQzuwUtY']


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
        if REF(C[i], 0) < ma5 or REF(C[i], 0) < ma13 or REF(C[i], 0) < ma21 or REF(C[i], 0) < ma34:
            continue

        ret = (COUNT((C[i] > MA(C[i], 5)) & (C[i] > MA(C[i], 13)) & (C[i] > MA(C[i], 21)) & (C[i] > MA(C[i], 34)), n) == 1)
        # print(i, ret, candidate, get_current_date(), select_by_volume(21), COUNT(select_buy_signal(0), 34), COUNT(100 * (C[i] - REF(C[i], 1)) / REF(C[i], 1) >= 3., 55))
        if ret and select_by_volume(21) and COUNT(select_buy_signal(0), 34) >= 1 and (COUNT(100 * (C[i] - REF(C[i], 1)) / REF(C[i], 1) >= 3., 55) >= 4):
            _, peers = zig_helper(C.series[-(i+1):], 7)
            # print(i, ret, candidate, peers, get_current_date(), select_by_volume(13), COUNT(select_buy_signal(0), 15), COUNT(100 * (C[i] - REF(C[i], 1)) / REF(C[i], 1) >= 3., 55))
            # 美股可能会在底部多次震荡，这里不判断peers的数量，区别于A股
            candidate = candidate + 1
                # print(candidate, get_current_date(), symbol(get_current_security()), i, ma55, peers)
                # print(C.series[-(i+1):])
        # if ret:
        #     print(get_current_date(), symbol(get_current_security()), "突破5\\13\\21\\34\\55日均线", C, ma5)

    return candidate >= 1


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


# 长期均线13\34连续n天形成上升趋势
def select_long_average_up(n):
    model = LinearRegression()
    y_train = []
    for i in range(n - 1, -1, -1):
        y_train.append(MA(C[i], 13).value)
    try:
        model.fit(np.array(range(len(y_train))).reshape(-1, 1), np.array(y_train).reshape(-1, 1))
    except Exception as e:
        print(e, y_train)
    ma34_coef = model.coef_

    # print(ma34_coef, y_train)
    y_train = []
    for i in range(n - 1, -1, -1):
        y_train.append(MA(C[i], 34).value)
    try:
        model.fit(np.array(range(len(y_train))).reshape(-1, 1), np.array(y_train).reshape(-1, 1))
    except Exception as e:
        print(e, y_train)
    ma55_coef = model.coef_

    # print(ma34_coef, ma55_coef)
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
            if select_over_average(31) and select_long_average_up(5) and select_down_from_max(31, 1.12) and HHV(H, 21) / C > 1.12:
                if time_tmp == "":
                    time_tmp = time
                elif int(time) - int(time_tmp) < 23:  # interval between adjacent choosing must large than 23 days
                    continue

                tcnt = tcnt + 1
                # print("select {} at {}".format(sym, time))
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

    with open('us_daily_stock', 'a+') as fp:
        fp.write(rw + "\n")


day = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d')
day0 = (datetime.datetime.now() + datetime.timedelta(days=-3)).strftime('%Y%m%d')

set_data_backend(AkshareUSDataBackend())
data_backend = funcat_execution_context.get_data_backend()
trading_dates = data_backend.get_trading_dates("20150808", day)
S("UVIX")
T("20240722")
print(O, H, L, C)
print(select_over_average(31))
print(select_long_average_up(5))
print(select_down_from_max(31, 1.12) and HHV(H, 21) / C > 1.12)

with open('us_daily_stock', 'w') as fp:
    fp.write("美股选股(共114只热门股及ETF，30日内5%以上盈利视为准确):\n")

select(
   lambda: select_over_average(31) and select_long_average_up(5) and select_down_from_max(31, 1.12) and HHV(H, 21) / C > 1.12,
   start_date=trading_dates[-1],
   end_date=trading_dates[-1],
   callback=callback,
)

if not os.path.exists('us_daily_stock'):
    raise Exception('daily_stock no such file...')
else:
    with open('us_daily_stock', 'r') as fp:
        text = fp.read()
        text = text + "\n\n注意：\n美股趋势一但形成很难扭转，本选股策略只会挑选趋势反转的股票，注意止盈止损"
