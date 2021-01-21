# -*- coding: utf-8 -*-
#

from cached_property import cached_property

import pandas as pd
import numpy as np
import datetime
import requests
import json
import os

from .rt_data import get_runtime_data
from .backend import DataBackend
from ..utils import lru_cache, get_str_date_from_int, get_int_date


class TencentDataBackend(DataBackend):

    def __init__(self, freq):
        if freq[-1] == 'm':
            self.freq = int(freq[:-1]) * 60
        else:
            raise "Only support minutes level of stock kline."

    @cached_property
    def ts(self):
        try:
            import tushare as ts
            return ts
        except ImportError:
            print("-" * 50)
            print(">>> Missing tushare. Please run `pip install tushare`")
            print("-" * 50)
            raise

    @cached_property
    def stock_basics(self):
        return self.ts.pro_api().stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date').set_index('symbol', drop=True)

    @cached_property
    def code_name_map(self):
        code_name_map = self.stock_basics[["name"]].to_dict()["name"]
        return code_name_map

    @cached_property
    def trading_dates(self):
        now = datetime.date.today().strftime("%Y%m%d")
        pro = self.ts.pro_api()
        df = pro.query('trade_cal', start_date="20100808", end_date=now, is_open=1)
        trading_dates = [get_int_date(date) for date in df['cal_date'].tolist()]
        return trading_dates

    def convert_code(self, order_book_id):
        return order_book_id.split(".")[0]

    @lru_cache()
    def get_trading_dates(self, start, end):
        """获取所有的交易时间戳
        tencent api只能获取最近480条记录, 由于交易时间只占全天时间的1/6，所以获取
        离end时间最近的4000条时间戳，然后再筛选有效时间戳

        :param start: 20210101093000
        :param end: 20210119150000
        """
        if len(str(end)) == 14:
            start = datetime.datetime.strptime(str(end), "%Y%m%d%H%M%S") + datetime.timedelta(seconds=-self.freq*4000)
            end = datetime.datetime.strptime(str(end), "%Y%m%d%H%M%S")
        else:
            end = get_str_date_from_int(end)+'150000'

        date_list = []
        be = start.strftime("%Y%m%d%H%M%S")
        en = end.strftime("%Y%m%d%H%M%S")
        while be <= en:
            # print("++", be, en, "++", be[:8])
            if int(be[:8]) not in self.trading_dates or int(be[8:]) < 93000 or int(be[8:]) > 150000:
                be = datetime.datetime.strptime(str(be), "%Y%m%d%H%M%S") + datetime.timedelta(seconds=self.freq)
                be = be.strftime("%Y%m%d%H%M%S")
                continue
            date_list.append(int(be))
            be = datetime.datetime.strptime(str(be), "%Y%m%d%H%M%S") + datetime.timedelta(seconds=self.freq)
            be = be.strftime("%Y%m%d%H%M%S")

        return date_list

    @lru_cache(maxsize=4096)
    def get_price(self, order_book_id, start, end, freq):
        """
        :param order_book_id: e.g. 000002.SZ
        :param start: 20190101
        :param end: 20190201
        :returns:
        :rtype: numpy.rec.array
        """
        url = "http://ifzq.gtimg.cn/appstock/app/kline/mkline?param="

        ktype = freq
        if freq[-1] == "m":
            ktype = freq[:-1]
            if len(str(end)) == 8:
                end = int(str(end) + "150000")
        elif freq == "1d":
            ktype = "D"
        # else W M

        now = datetime.date.today().strftime("%Y%m%d%H%M%S")
        end = now if end is None else end

        print(start, end)

        if freq[-1] == "m":
            str_suffix = freq[-1] + ktype

        code_suffix = order_book_id[-2:].lower() + order_book_id[:-3]
        text = requests.get(url + code_suffix + "," + str_suffix)
        if text.status_code == 200:
            raw = json.loads(text.text)
            df = pd.DataFrame(raw['data'][code_suffix][str_suffix])
            df.rename(columns={0:"trade_date", 1:"open", 2:"close", 3:"high", 4:"low", 5:"vol"}, inplace=True)
            if df is None:
                return np.array([])
                
        df["datetime"] = df["trade_date"].apply(lambda x: int(x.replace("-", "")) * 100)
        df = df.loc[df['datetime'] <= end]
        df = df.sort_index(ascending=False)
        df.reset_index(inplace=True, drop=True)
        df = df.sort_index(ascending=False)
        print(df)
        arr = df.to_records()

        return arr

    @lru_cache()
    def get_order_book_id_list(self):
        """获取所有的股票代码列表
        """
        pro = self.ts.pro_api()
        info = pro.query('stock_basic', exchange='', list_status='L', field='ts_code')
        order_book_id_list = info['ts_code'].tolist()
        return order_book_id_list

    @lru_cache(maxsize=4096)
    def symbol(self, order_book_id):
        """获取order_book_id对应的名字
        :param order_book_id str: 股票代码
        :returns: 名字
        :rtype: str
        """
        code = self.convert_code(order_book_id)
        return "{}[{}]".format(order_book_id, self.code_name_map.get(code))
