import os
import json
import time
import requests
import pandas as pd
import tushare as ts
import datetime

from funcat import *
from funcat.context import ExecutionContext as funcat_execution_context


def callback(date, order_book_id, sym):
    start_date = (datetime.datetime.strptime(str(date), "%Y%m%d") + datetime.timedelta(days=-60)).strftime("%Y%m%d")
    dt = df.loc[(df["select_date"] <= date) & (df["select_date"] >= int(start_date))]
    st = list(set(dt["ts_code"].tolist()))

    first_found = False
    # current stock gives buy signal 2 months ago.
    if order_book_id in st:
        order_df = dt.loc[dt["ts_code"] == order_book_id].reset_index(drop=True)
        select_date = order_df.at[0, "select_date"]

        fdate = datetime.datetime.strptime(str(select_date), "%Y%m%d")

        url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000001,day,{},,640,qfq".format(fdate.strftime("%Y-%m-%d"))
        text = requests.get(url)

        if text.status_code == 200:
            raw = json.loads(text.text)
            idxs = raw['data']['sh000001']['day']

            for cur_date in trading_dates[trading_dates.index(select_date) : trading_dates.index(date) + 1]:
                for idx in idxs:
                    if idx[0].replace("-", "") == str(cur_date):
                        break

                T(cur_date)
                idx = list(map(lambda x: float(x), idx[1:]))
                idx_pct_chg = round((idx[1] - idx[0]) / idx[0] * 100, 2)

                deviation = round(R.value - float(idx_pct_chg), 2)

                # current stock deviate of 3% from the index. Got it!
                if deviation > 3.:
                    if cur_date == date and not first_found:
                        print(date, sym, "select_date:", select_date)
                        with open('daily_stock', 'a+') as fp:
                            rw = date
                            fp.write(sym + " 首次筛选关注时间: " + str(select_date) + "\n")

                    first_found = True


df = pd.read_csv("statistics.csv", index_col=False)
print(df)

day = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d')
day0 = (datetime.datetime.now() + datetime.timedelta(days=-3)).strftime('%Y%m%d')

data_backend = funcat_execution_context.get_data_backend()
trading_dates = data_backend.get_trading_dates("20150808", day)
order_book_id_list = data_backend.get_order_book_id_list()

with open('daily_stock', 'a+') as fp:
    fp.write("\n二次筛选（捕捉长期趋势股，不计算历史准确率）:\n")

select(
   lambda: R > 0,
   start_date=trading_dates[-1],
   end_date=trading_dates[-1],
   callback=callback,
)
