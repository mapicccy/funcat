import time
import akshare as ak
import numpy as np
import pandas as pd
import datetime
import requests
import mplfinance as mpf

from sklearn.linear_model import LinearRegression
from funcat import *
from funcat.account import Account
from funcat.context import ExecutionContext as funcat_execution_context

day = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d')
day0 = (datetime.datetime.now() + datetime.timedelta(days=-3)).strftime('%Y%m%d')

set_data_backend(AkshareFutureDataBackend())
data_backend = funcat_execution_context.get_data_backend()
trading_dates = data_backend.get_trading_dates("20150808", day)
order_book_id_list = data_backend.get_order_book_id_list()

with open('futures_daily_stock', 'r') as fp:
    while True:
        line = fp.readline()
        if line is None:
            break

        if len(line.split(" ")) < 4:
            continue

        date = line.split(" ")[0]
        symfull = line.split(" ")[1]
        sym = symfull.split("[")[0]
        S(sym)
        T(day)

        stage = trading_dates[len(trading_dates) - len(O.series):]
        print(len(stage), len(O.series))
        data = {
            'Date': stage,
            'Open': O.series,
            'High': H.series,
            'Low': L.series,
            'Close': C.series,
            'Volume': V.series
        }

        cond = data["Date"] == date
        data['Date'] = pd.to_datetime(data['Date'])
        df = pd.DataFrame(data)
        df.set_index('Date', inplace=True)
        buy_plot = [
            mpf.make_addplot(data[cond].index, scatter=True, markersize=1000, marker='^', color='r')
        ]

        filename = "/home/ec2-user/public/futures/{}.png".format(symfull)
        mpf.plot(df, type='candle', style='charles', volume=True, mav=(5, 20), title=symfull, addplot=buy_plot, savefig=dict(fname=filename, dpi=300))

