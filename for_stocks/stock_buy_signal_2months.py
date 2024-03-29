import os
import tushare as ts
import numpy as np
import pandas as pd
import datetime
import time

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


# 通达信八仙过海买入指标，趋势跟随
def select_buy_signal(n):
    return ((ZIG(C[n], 6) > REF(ZIG(C[n], 6), 1) and REF(ZIG(C[n], 6), 1) <= REF(ZIG(C[n], 6), 2) <= REF(
        ZIG(C[n], 6), 3) or (
                     ZIG(C[n], 22) > REF(ZIG(C[n], 22), 1) and REF(ZIG(C[n], 22), 1) <= REF(ZIG(C[n], 22), 2) <= REF(ZIG(C[n], 22),
                                                                                                         3))))


# 通达信八仙过海卖出指标，趋势跟随
def select_sell_signal():
    return ((ZIG(C, 6) < REF(ZIG(C, 6), 1) and REF(ZIG(C, 6), 1) >= REF(ZIG(C, 6), 2) >= REF(
        ZIG(C, 6), 3) or (
                     ZIG(C, 22) < REF(ZIG(C, 22), 1) and REF(ZIG(C, 22), 1) >= REF(ZIG(C, 22), 2) >= REF(ZIG(C, 22),
                                                                                                         3))))


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
    return (ma34_coef > 0.005 or ma55_coef > 0.005) and (ma34_coef + ma55_coef) > -0.1


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
    global df

    try:
        index_df = ts.pro_bar(ts_code='000001.SH', asset="I", start_date=str(date), end_date=str(date))
    except IOError as e:
        time.sleep(60)
        return
    df = df.append([{'select_date': date, 'ts_code': order_book_id, 'symbol': sym, 'pct_chg': round((C.value - REF(C, 1).value) / REF(C, 1).value, 3), 'index_pct_chg': index_df.at[0, 'pct_chg']}], ignore_index=True)

    df.to_csv('statistics.csv')
    print(date, sym)


# data area, 2 months - today
day = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d')
day0 = (datetime.datetime.now() + datetime.timedelta(days=-60)).strftime('%Y%m%d')

data_backend = funcat_execution_context.get_data_backend()
trading_dates = data_backend.get_trading_dates("20150808", day)
order_book_id_list = data_backend.get_order_book_id_list()

df = pd.DataFrame(columns=['select_date', 'ts_code', 'symbol', 'pct_chg', 'index_pct_chg'])

select(
   lambda: select_over_average(31) and select_long_average_up(5) and select_down_from_max(31, 1.12) and HHV(H, 21) / C > 1.12,
   start_date=day0,
   end_date=trading_dates[-1],
   callback=callback,
)
