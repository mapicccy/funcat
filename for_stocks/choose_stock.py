import os
import time
import tushare as ts
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
    pro = ts.pro_api()
    df = pro.query('daily_basic', ts_code=order_book_id,
                   fields='ts_code,trade_date,turnover_rate,volume_ratio,pe,pb,total_mv,circ_mv,float_share')

    count = 0
    for i in range(21):
        if df.at[i, 'turnover_rate'] <= 1:
            count = count + 1

    # 最近31交易日换手率低于1%的天数大于13天、涨幅超过3%的天数小于6，直接返回
    if count > 13 and COUNT(R > 3., 31) < 6:
        return

    coef = select_macd_cross_up()

    rw = sym + " "

    if os.path.exists("statistics.csv"):
        dt = pd.read_csv("statistics.csv", index_col=False)
        cur_dt = pd.DataFrame(columns=['select_date', 'ts_code', 'symbol', 'pct_chg', 'index_pct_chg'])
        cur_dt = pd.concat([cur_dt, pd.DataFrame([{'select_date': date, 'ts_code': order_book_id, 'symbol': sym, 'pct_chg': round((C.value - REF(C, 1).value) / REF(C, 1).value, 3), 'index_pct_chg': 0}])], ignore_index=True)
        dt = pd.concat([cur_dt, dt], ignore_index=True)
        dt.to_csv("statistics.csv", index=0)

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

    with open('daily_stock', 'a+') as fp:
        fp.write(rw + "\n")


day = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d')
day0 = (datetime.datetime.now() + datetime.timedelta(days=-3)).strftime('%Y%m%d')

set_data_backend(TushareDataBackend())
data_backend = funcat_execution_context.get_data_backend()
trading_dates = data_backend.get_trading_dates("20150808", day)
print(trading_dates)
order_book_id_list = data_backend.get_order_book_id_list()

with open('daily_stock', 'w') as fp:
    fp.write("首次筛选（捕捉短期牛股，30日内5%以上盈利视为准确）:\n")

select(
   lambda: select_over_average(31) and select_long_average_up(5) and select_down_from_max(31, 1.12) and HHV(H, 21) / C > 1.12,
   start_date=trading_dates[-1],
   end_date=trading_dates[-1],
   callback=callback,
)

os.system('/root/miniconda3/envs/py39/bin/python -u /root/project/funcat/for_stocks/stock_sift.py')
url = "http://qt.gtimg.cn/q="
with open('daily_stock', 'a+') as fp:
    fp.write("\n大象起舞(市值超500亿，量能狂飙):\n")
for code in order_book_id_list:
    if code > "688000.SH":
        break

    code_suffix = code[-2:].lower() + code[:-3]
    text = requests.get(url + code_suffix)
    if text.status_code == 200:
        raw = text.text.split("~")
        print(code, raw[44])
        if raw[44] != "":
            total_mv = float(raw[44])
            # 总市值大于500亿
            if total_mv > 500:
                S(code)
                T(trading_dates[-1])
                # 阳线且成交量大于过去5天的评价成交量的两倍
                if float(raw[3]) > float(raw[5]) and float(raw[36]) > 2 * MA(V, 5):
                    with open('daily_stock', 'a+') as fp:
                        fp.write(code + "\n")

df = pd.read_csv("statistics.csv", index_col=False)
sd = (datetime.datetime.strptime(str(day), "%Y%m%d") + datetime.timedelta(days=-60)).strftime("%Y%m%d")
dt = df.loc[(df["select_date"] <= int(day)) & (df["select_date"] >= int(sd))]
st = list(set(dt["ts_code"].tolist()))
stat = {}
for i in st:
    dtmp = dt.loc[dt["ts_code"] == i].reset_index(drop=True)
    time_list = list(set(dtmp["select_date"].tolist()))
    # get the nearest selection
    time = time_list[0]
    S(i)
    T(time)
    price = C.value
    # day is today, due to tushare api limitation, this data may be NaN
    T(day)
    try:
        stat[i] = int(round((C.value - price) / price, 2) * 100)
    except Exception as e:
        print(e)
sorted_stock = sorted(stat.items(), key=lambda x:-x[1])


ATT = """\n注意：\n1. 已屏蔽换手率过低以及不活跃股票，仅供参考\n2. 不要选ST股票、MA55/MA120长期均线走势弯折（操纵迹象明显）\n3. 资金介入明显\n4. 回测2020/01/01至今，所有选出股票在30个交易日之后3228只盈利，2150只亏损，胜率60%，最大单只盈利541%，最大单只亏损-46%\n5. 参考1-3，可以提高胜率，将测试盈利与否的30交易日延长，胜率会逼近87%，侧面说明大盘长期向上\n6. 历史数据显示，如果首次筛选选出较多的股票，代表大盘临近上涨趋势点\n7. 如果您有更好的交易\选股策略，苦于没有编程经验，请联系微信zhao9111，独家服务帮您实现\n8. tushare数据源获取成本大幅提高，股票池固化在2023/05/24，总共5193只，后续不再更新股票池\n"""
with open('daily_stock', 'a+') as fp:
    fp.write("\n近2月内程序选出牛股TOP5:\n")
    s = ""
    for i in range(5):
        if sorted_stock and len(sorted_stock) > i:
            dtmp = dt.loc[dt["ts_code"] == sorted_stock[i][0]].reset_index(drop=True)
            s = s + str(symbol(sorted_stock[i][0])) + " 选出日:" + str(dtmp.at[0, "select_date"]) + "，至今涨幅" + str(sorted_stock[i][1]) + "%\n"

    if s != "":
        fp.write(s)
    fp.write(ATT)
