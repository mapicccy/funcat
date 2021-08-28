#!/root/miniconda3/envs/py36/bin/python3
import time
import tushare as ts
import datetime

from funcat import *

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import NVARCHAR, Float, Integer
from wxpusher import WxPusher as wx


uid = ['UID_4yb8qx3oxePh1ZHCvFpVxNGDRAuf',
        'UID_6tyjJDIh80gYNw43z6sTkmMhsJWV',
        'UID_x1ArbpSoVqdcRr8EHTJYPQzuwUtY',
        'UID_x1ArbpSoVqdcRr8EHTJYPQzuwUtY',
        'UID_riafQC67rAZFEkCYdR0tNJICZgrw',
        'UID_dZkZx0yYMOBiCavWZ5B16jCl8mH1',
        'UID_1HaztzY0IMUIXW13HxlbPzIelXuZ',
        'UID_05yCFqGgNwzx3QKCLD5Jdkp87fWh',
        'UID_lWAVOTvQLh3dfnIRBhM8IuX9n2K3']

start = "20120801"
end = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d')
data_backend = funcat_execution_context.get_data_backend()
trading_dates = data_backend.get_trading_dates(start, end)
order_book_id_list = data_backend.get_order_book_id_list()

freq = 0
engine_ts = create_engine('mysql+mysqlconnector://root:@localhost:3306/ts_stock_basic')
conn = engine_ts.connect()
for ts_code in order_book_id_list:
    freq = freq + 1

    if freq == 100:
        time.sleep(61)
        freq = 0

    pro = ts.pro_api()
    df = pro.stk_holdernumber(ts_code=ts_code, start_date="20120101")

    dtype = {
        "ts_code": NVARCHAR(length=20),
        "ann_date": NVARCHAR(length=20),
        "end_date": NVARCHAR(length=20),
        "holder_num": Integer(),
    }

    df.to_sql('holdernumber', engine_ts, index=False, if_exists='append', chunksize=5000, dtype=dtype)

conn.execute("create table tmp select * from holdernumber group by ts_code,ann_date,end_date,holder_num")
conn.execute("drop table holdernumber")
conn.execute("alter table tmp rename to holdernumber")
proxy = conn.execute("select count(*) from holdernumber")
text = "更新mysql数据库股东人数成功，共" + str(proxy.fetchall()) + "条目"
wx.send_message(text, uids=uid, token='')

freq = 0
for ts_code in order_book_id_list:
    freq = freq + 1

    if freq == 10:
        time.sleep(61)
        freq = 0

    pro = ts.pro_api()
    df = pro.top10_floatholders(ts_code=ts_code, start_date=start)

    dtype = {
        "ts_code": NVARCHAR(length=20),
        "ann_date": NVARCHAR(length=20),
        "end_date": NVARCHAR(length=20),
        "holder_name": NVARCHAR(length=64),
        "hold_amount": BigInteger(),
    }

    df.to_sql('top10_floatholders', engine_ts, index=False, if_exists='append', chunksize=5000, dtype=dtype)

conn.execute("create table tmp select * from top10_floatholders group by ts_code,ann_date,end_date,holder_name,hold_amount")
conn.execute("drop table top10_floatholders")
conn.execute("alter table tmp rename to top10_floatholders")
proxy = conn.execute("select count(*) from top10_floatholders")
text = "更新mysql数据库十大流通股东持股成功，共" + str(proxy.fetchall()) + "条目"
wx.send_message(text, uids=uid, token='')
