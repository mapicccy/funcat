import os
import time
import tushare as ts
import numpy as np
import pandas as pd
import datetime
from wxpusher import WxPusher as wx

from funcat import *
from funcat.account import Account
from funcat.context import ExecutionContext as funcat_execution_context


day = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d')
day0 = (datetime.datetime.now() + datetime.timedelta(days=-5)).strftime('%Y%m%d')

set_data_backend(AkshareDataBackend())
data_backend = funcat_execution_context.get_data_backend()
trading_dates = data_backend.get_trading_dates("20150808", day)
order_book_id_list = data_backend.get_order_book_id_list()

backward = 60

df = pd.read_csv("statistics.csv", index_col=False)
sd = (datetime.datetime.strptime(str(day), "%Y%m%d") + datetime.timedelta(days=-backward)).strftime("%Y%m%d")
dt = df.loc[(df["select_date"] <= int(day0)) & (df["select_date"] >= int(sd))]
st = list(set(dt["ts_code"].tolist()))
stat = {}
pro = []
for i in st:
    if i[:6] >= "800000":
        continue

    dtmp = dt.loc[dt["ts_code"] == i].reset_index(drop=True)
    time_list = list(set(dtmp["select_date"].tolist()))
    # get the nearest selection
    time = time_list[0]
    profit = 0
    S(i[:6])

    T(day)
    price = C.value

    T(time)
    price = C.value

    for j in range(backward, 5, -1):
        anchor = (datetime.datetime.strptime(str(day), "%Y%m%d") + datetime.timedelta(days=-j)).strftime("%Y%m%d")
        if anchor <= str(time):
            continue

        T(anchor)
        profit = max(int(round((C.value - price) / price, 2) * 100), profit)
        # print(i, time, anchor, profit)

    # day is today, due to tushare api limitation, this data may be NaN
    T(day)
    profit = max(int(round((C.value - price) / price, 2) * 100), profit)
    pro.append(profit)
    try:
        stat[i] = (int(round((C.value - price) / price, 2) * 100), profit)
    except Exception as e:
        print(e)
print(stat)
sorted_stock = sorted(stat.items(), key=lambda x:-x[1][0])
count = len([num for num in pro if num > 4])
t_count = len(sorted_stock)
ratio = round(float(count / t_count), 4) * 100

print(sorted_stock)
print("Total candidates: ", t_count, "profit: ", count)

t_profit = 0.
max_profit = sorted_stock[0][1][0]
max_loss = sorted_stock[-1][1][0]
with open('daily_stock', 'w+') as fp:
    s = ""
    for i in range(len(sorted_stock)):
        dtmp = dt.loc[dt["ts_code"] == sorted_stock[i][0]].reset_index(drop=True)
        s = s + str(symbol(sorted_stock[i][0][:6])) + " 选出日:" + str(dtmp.at[0, "select_date"]) + "，至今盈利" + str(sorted_stock[i][1][0]) + "%,"
        s = s + " 最高盈利" + str(sorted_stock[i][1][1]) + "%\n"
        t_profit = t_profit + sorted_stock[i][1][0]

    if s != "":
        fp.write(s)

t_profit = round(float(t_profit / t_count), 2)
text = f"近两个月程序共选出股票{t_count}只,达到预期涨幅(4%)的{count}只,占比{ratio}%\n所有股票选出日买入同等份额持有至今共盈利{t_profit}%\n所有股票最大盈利{max_profit}%,最大亏损{max_loss}%\n\n牛股TOP20：\n"
ATT = """\n注意：\n1. 已屏蔽换手率过低以及不活跃股票，仅供参考\n2. 不要选ST股票、MA55/MA120长期均线走势弯折（操纵迹象明显）\n3. 资金介入明显\n4. 回测2020/01/01至今，所有选出股票在30个交易日之后3228只盈利，2150只亏损，胜率60%，最大单只盈利541%，最大单只亏损-46%\n5. 参考1-3，可以提高胜率，将测试盈利与否的30交易日延长，胜率会逼近87%，侧面说明大盘长期向上\n6. 历史数据显示，如果首次筛选选出较多的股票，代表大盘临近上涨趋势点\n7. 如果您有更好的交易\选股策略，苦于没有编程经验，请联系微信zhao9111，独家服务帮您实现\n8. tushare数据源获取成本大幅提高，股票池固化在2023/05/24，总共5193只，后续不再更新股票池\n"""
with open('daily_stock', 'r') as fp:
    lines = fp.readlines()
    for i in range(20):
        text = text + lines[i]

    text = text + "\n\n熊股DOWN20：\n"
    for i in range(len(sorted_stock) - 20, len(sorted_stock)):
        text = text + lines[i]

text = text + ATT
print(text)

if int(day) not in trading_dates:
    wx.send_message(text, topic_ids=['8112'], token='AT_dmMmeBfDKT1tyV82aZvT98Vm4xNYx1M2')
