import os
import time
import tushare as ts
import numpy as np
import pandas as pd
import datetime
from tqdm import tqdm
from wxpusher import WxPusher as wx

from funcat import *
from funcat.account import Account
from funcat.context import ExecutionContext as funcat_execution_context


day = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d')

set_data_backend(AkshareDataBackend())
data_backend = funcat_execution_context.get_data_backend()
trading_dates = data_backend.get_trading_dates("20150808", day)

with open('daily_stock', 'a+') as fp:
    fp.write("\n二次筛选（捕捉短线强势股）:\n")

select(
   lambda: select_over_average(31) and select_long_average_up(5) and select_down_from_max(31, 1.12) and HHV(H, 21) / C > 1.12,
   start_date=trading_dates[-1],
   end_date=trading_dates[-1],
   callback=callback,
)
