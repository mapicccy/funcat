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
        """获取所有的交易日

        :param start: 20190101
        :param end: 20190201
        """
        s = 0
        e = len(self.trading_dates)
        for i in range(len(self.trading_dates)):
            if self.trading_dates[i] >= get_int_date(start):
                s = i
                break
        for i in range(len(self.trading_dates)):
            if self.trading_dates[i] > get_int_date(end):
                e = i
                break
        return self.trading_dates[s:e]

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

        is_index = False
        if ((order_book_id.startswith("0") and order_book_id.endswith(".SH")) or
            (order_book_id.startswith("39") and order_book_id.endswith(".SZ"))
            ):
            is_index = True
        ktype = freq
        if freq[-1] == "m":
            ktype = freq[:-1]
        elif freq == "1d":
            ktype = "D"
        # else W M

        now = datetime.date.today().strftime("%Y%m%d")
        end = now if end is None else end

        str_start_date = get_str_date_from_int(start)
        str_end_date = get_str_date_from_int(end)
        print(str_start_date, str_end_date)

        if is_index:
            pass
        else:
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
                
        df["datetime"] = df["trade_date"].apply(lambda x: int(x.replace("-", "")))
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
