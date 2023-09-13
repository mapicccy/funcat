import os
import time
import tushare as ts
import numpy as np
import pandas as pd
import datetime

from funcat import *
from funcat.account import Account
from funcat.context import ExecutionContext as funcat_execution_context


day = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d')
day0 = (datetime.datetime.now() + datetime.timedelta(days=-3)).strftime('%Y%m%d')

set_data_backend(TushareDataBackend())
data_backend = funcat_execution_context.get_data_backend()
trading_dates = data_backend.get_trading_dates("20150808", day)
order_book_id_list = data_backend.get_order_book_id_list()

backward = 60

df = pd.read_csv("statistics.csv", index_col=False)
sd = (datetime.datetime.strptime(str(day), "%Y%m%d") + datetime.timedelta(days=-backward)).strftime("%Y%m%d")
dt = df.loc[(df["select_date"] <= int(day)) & (df["select_date"] >= int(sd))]
st = list(set(dt["ts_code"].tolist()))
stat = {}
pro = []
for i in st:
    """
    if i != "002553.SZ":
        continue
    """
    dtmp = dt.loc[dt["ts_code"] == i].reset_index(drop=True)
    time_list = list(set(dtmp["select_date"].tolist()))
    # get the nearest selection
    time = time_list[0]
    profit = 0
    S(i)
    T(time)
    price = C.value

    for j in range(backward, 0, -1):
        anchor = (datetime.datetime.strptime(str(day), "%Y%m%d") + datetime.timedelta(days=-j)).strftime("%Y%m%d")
        if anchor <= str(time):
            continue

        T(anchor)
        profit = max(int(round((C.value - price) / price, 2) * 100), profit)
        # print(i, time, anchor, profit)

    if profit > 4:
        pro.append(profit)
    else:
        pro.append(-1)

    # day is today, due to tushare api limitation, this data may be NaN
    T(day)
    try:
        stat[i] = int(round((C.value - price) / price, 2) * 100)
    except Exception as e:
        print(e)
sorted_stock = sorted(stat.items(), key=lambda x:-x[1])
count = len([num for num in pro if num > 0])

print(sorted_stock)
print("Total candidates: ", len(sorted_stock), "profit: ", count)

with open('daily_stock', 'w+') as fp:
    s = ""
    for i in range(len(sorted_stock)):
        dtmp = dt.loc[dt["ts_code"] == sorted_stock[i][0]].reset_index(drop=True)
        s = s + str(symbol(sorted_stock[i][0])) + " 选出日:" + str(dtmp.at[0, "select_date"]) + "，至今涨幅" + str(sorted_stock[i][1]) + "%, 选出后最高盈利 " + str(pro[i]) + "\n"

    if s != "":
        fp.write(s)
