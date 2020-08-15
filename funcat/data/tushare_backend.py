# -*- coding: utf-8 -*-
#

from cached_property import cached_property

import pandas as pd
import numpy as np
import datetime
import os

from .backend import DataBackend
from ..utils import lru_cache, get_str_date_from_int, get_int_date


class TushareDataBackend(DataBackend):

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
        return self.ts.get_stock_basics()

    @cached_property
    def code_name_map(self):
        code_name_map = self.stock_basics[["name"]].to_dict()["name"]
        return code_name_map

    def convert_code(self, order_book_id):
        return order_book_id.split(".")[0]

    @lru_cache()
    def get_trading_dates(self, start, end):
        """获取所有的交易日

        :param start: 20160101
        :param end: 20160201
        """
        pro = self.ts.pro_api()
        df = pro.query('trade_cal', start_date=start, end_date=end, is_open=1)
        trading_dates = [get_int_date(date) for date in df['cal_date'].tolist()]
        return trading_dates

    @lru_cache(maxsize=4096)
    def get_price(self, order_book_id, start, end, freq):
        """
        :param order_book_id: e.g. 000002.XSHE
        :param start: 20160101
        :param end: 20160201
        :returns:
        :rtype: numpy.rec.array
        """
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

        if end is None:
            end = datetime.date.today().strftime("%Y%m%d")

        str_start_date = get_str_date_from_int(start)
        str_end_date = get_str_date_from_int(end)
        filename = (order_book_id + str_start_date + str_end_date).replace('.', '-') + '.csv'
        if os.path.exists('data'):
            if os.path.exists('data/' + filename):
                df = pd.read_csv('data/' + filename)
            else:
                update_to_date = datetime.date.today().strftime("%Y%m%d")
                trading_dates = self.get_trading_dates(start, update_to_date)
                last_trading_date = get_str_date_from_int(trading_dates[-1])
                ad_filename = order_book_id.replace('.', '-') + '2018-04-01' + last_trading_date + '.csv'
                if os.path.exists('data/' + ad_filename):
                    df = pd.read_csv('data/' + ad_filename)
                    df = df.loc[df['trade_date'] <= end]
        else:
            os.mkdir('data')

        if 'df' not in dir():
            if is_index:
                df = self.ts.pro_bar(ts_code=order_book_id, asset='I', start_date=str_start_date, end_date=str_end_date)
            else:
                df = self.ts.pro_bar(ts_code=order_book_id, adj='qfq', start_date=str_start_date, end_date=str_end_date)

            if df is None:
                return np.array([])

            if freq[-1] == "m":
                df["datetime"] = df.apply(
                    lambda row: int(row["trade_date"].split(" ")[0].replace("-", "")) * 1000000 + int(row["trade_date"].split(" ")[1].replace(":", "")) * 100, axis=1)
            elif freq in ("1d", "W", "M"):
                df["datetime"] = df["trade_date"].apply(lambda x: int(x.replace("-", "")) * 1000000)

            df.to_csv('data/' + filename, index=False)

        df = df.sort_index(ascending=False)
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
