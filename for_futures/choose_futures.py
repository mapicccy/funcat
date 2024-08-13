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


# m天的实体最高价比m天的实体最低价高n%
def select_down_from_max(m, n):
    return HHV(MAX(O, C), m) / LLV(MIN(O, C), m) >= n

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
        if len(C[i].series) < 55:
            return False

        ma5 = MA(C[i], 5)
        ma13 = MA(C[i], 13)
        ma21 = MA(C[i], 21)
        ma34 = MA(C[i], 34)
        ma55 = MA(C[i], 55)
        if REF(C[i], 0) < ma5 or REF(C[i], 0) < ma13 or REF(C[i], 0) < ma21 or REF(C[i], 0) < ma34 or REF(C[i], 0) < ma55:
            continue

        ret = (COUNT((C[i] > MA(C[i], 5)) & (C[i] > MA(C[i], 13)) & (C[i] > MA(C[i], 21)) & (C[i] > MA(C[i], 34)) & (C[i] > MA(C[i], 55)), n) == 1)
        # 期货自带杠杆，去掉涨幅3.5%次数的判断，非常难达到
        if ret and COUNT(select_buy_signal(0), 34) >= 1:
            _, peers = zig_helper(C.series[-(i+1):], 7)
            # print(i, ret, candidate, peers, get_current_date(), select_by_volume(13), COUNT(select_buy_signal(0), 15), COUNT(100 * (C[i] - REF(C[i], 1)) / REF(C[i], 1) >= 3., 55))
            if len(peers) <= 3:
                candidate = candidate + 1
                # print(candidate, get_current_date(), symbol(get_current_security()), i, ma55, peers)
                # print(C.series[-(i+1):])
        # if ret:
        #     print(get_current_date(), symbol(get_current_security()), "突破5\\13\\21\\34\\55日均线", C, ma5)

    return candidate == 1

# n天内存在第一次高于收盘价低于5\13\21\34\55日线
def select_below_average(n):
    candidate = 0
    for i in range(n):
        if len(C[i].series) < 55:
            return False

        ma5 = MA(C[i], 5)
        ma13 = MA(C[i], 13)
        ma21 = MA(C[i], 21)
        ma34 = MA(C[i], 34)
        ma55 = MA(C[i], 55)
        if REF(C[i], 0) > ma5 or REF(C[i], 0) > ma13 or REF(C[i], 0) > ma21 or REF(C[i], 0) > ma34 or REF(C[i], 0) > ma55:
            continue

        ret = (COUNT((C[i] <= MA(C[i], 5)) & (C[i] <= MA(C[i], 13)) & (C[i] <= MA(C[i], 21)) & (C[i] <= MA(C[i], 34)) & (C[i] <= MA(C[i], 55)), n) == 1)
        # 期货自带杠杆，去掉涨幅3.5%次数的判断，非常难达到。做空趋势不判断其它指标
        if ret:
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

    # print(ma34_coef, ma55_coef)
    return ma34_coef > 0. or ma55_coef > 0.

# 长期均线34\55连续n天形成下降趋势
def select_long_average_down(n):
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

    # print(ma34_coef, ma55_coef)
    return ma34_coef < 0. or ma55_coef < 0.


def callback_up(date, order_book_id, sym):
    if os.path.exists("futures.csv"):
        dt = pd.read_csv("futures.csv", index_col=False)
        cur_dt = pd.DataFrame(columns=['select_date', 'ts_code', 'symbol', 'pct_chg', 'index_pct_chg', "dir"])
        cur_dt = cur_dt.append([{'select_date': DATETIME.value, 'ts_code': order_book_id, 'symbol': sym, "dir": 1}], ignore_index=True)
        dt = pd.concat([cur_dt, dt], ignore_index=True)
        dt.to_csv("futures.csv", index=0)

    print(order_book_id, sym)
    with open('futures_daily_stock', 'a+') as fp:
        fp.write(str(DATETIME.value) + " " + sym + " 方向: 做多" + "\n")

def callback_down(date, order_book_id, sym):
    if os.path.exists("futures.csv"):
        dt = pd.read_csv("futures.csv", index_col=False)
        cur_dt = pd.DataFrame(columns=['select_date', 'ts_code', 'symbol', 'pct_chg', 'index_pct_chg', "dir"])
        cur_dt = cur_dt.append([{'select_date': DATETIME.value, 'ts_code': order_book_id, 'symbol': sym, "dir": 0}], ignore_index=True)
        dt = pd.concat([cur_dt, dt], ignore_index=True)
        dt.to_csv("futures.csv", index=0)

    print(order_book_id, sym)
    with open('futures_daily_stock', 'a+') as fp:
        fp.write(str(DATETIME.value) + " " + sym + " 方向: 做空" + "\n")

day = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d')
day0 = (datetime.datetime.now() + datetime.timedelta(days=-3)).strftime('%Y%m%d')

set_data_backend(AkshareFutureDataBackend())
data_backend = funcat_execution_context.get_data_backend()
trading_dates = data_backend.get_trading_dates("20150808", day)
order_book_id_list = data_backend.get_order_book_id_list()

S("JM2409")
T("20231212")
print(select_below_average(31))
print(select_long_average_down(3))
print(select_down_from_max(17, 1.05))

with open('futures_daily_stock', 'w') as fp:
    fp.write("期货策略:\n")

# Selecting futures contracts that can be traded on a long position
select(
   lambda: select_over_average(31) and select_long_average_up(3) and select_down_from_max(17, 1.05) and HHV(H, 21) / C > 1.05,
   start_date=trading_dates[-1],
   end_date=trading_dates[-1],
   callback=callback_up,
)

# Selecting futures contracts that can be traded on a short position
select(
   lambda: select_below_average(31) and select_long_average_down(3) and select_down_from_max(17, 1.05) and C / LLV(L, 21) > 1.05,
   start_date=trading_dates[-1],
   end_date=trading_dates[-1],
   callback=callback_down,
)

with open('futures_daily_stock', 'a+') as fp:
    text = "\n\n注意：\n1. 期货自带杠杆，注意风险\n2. 本策略选择可以做多或者做空的品种，注意甄别方向\n3. 标的选择会择机，可能会出现数天没有买入标的的情况，需要耐心等待\n"
    fp.write(text)

if not os.path.exists('futures_daily_stock'):
    raise Exception('futures_stock no such file...')
else:
    with open('futures_daily_stock', 'r') as fp:
        text = fp.read()
        wx.send_message(text, uids=uid, token='AT_dmMmeBfDKT1tyV82aZvT98Vm4xNYx1M2')
        wx.send_message(text, topic_ids=['10674'], token='AT_dmMmeBfDKT1tyV82aZvT98Vm4xNYx1M2', verify='true')
