# -*- coding: utf-8 -*-
#

from cached_property import cached_property

import pandas as pd
import numpy as np
import datetime
import time
import os

from .backend import DataBackend
from ..utils import lru_cache, get_str_date_from_int, get_int_date


class AkshareHKDataBackend(DataBackend):

    @cached_property
    def ak(self):
        try:
            import akshare as ak
            return ak
        except ImportError:
            print("-" * 50)
            print(">>> Missing akshare. Please run `pip install akshare --upgrade`")
            print("-" * 50)
            raise

    @cached_property
    def trading_dates(self):
        now = datetime.date.today()
        df = self.ak.stock_hk_daily(symbol='00388', adjust='qfq')
        # trade_date is an instance of datetime
        df = df.loc[df["date"] <= now]
        trading_dates = [get_int_date(date) for date in df['date'].tolist()]
        return sorted(trading_dates)

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
        is_index = False
        if ((order_book_id.startswith("0") and order_book_id.endswith(".SH")) or
            (order_book_id.startswith("39") and order_book_id.endswith(".SZ"))
            ):
            is_index = True
        is_found = False
        if ((order_book_id.startswith("5") and order_book_id.endswith(".SH")) or
            (order_book_id.startswith("1") and order_book_id.endswith(".SZ"))
            ):
            is_found = True
        ktype = freq
        if freq[-1] == "m":
            ktype = freq[:-1]
        elif freq == "1d":
            ktype = "D"
        # else W M

        now = datetime.date.today().strftime("%Y%m%d")
        last_tradeday = self.get_trading_dates(start, end)[-2]
        end = now if end is None else end

        str_start_date = get_str_date_from_int(start)
        str_end_date = get_str_date_from_int(end)
        filename = (order_book_id + str_start_date + str_end_date).replace('.', '-') + '.csv'
        if os.path.exists('data'):
            if os.path.exists('data/' + filename):
                # csv file may be empty, raise except EmptyDataError
                try:
                    df = pd.read_csv('data/' + filename)
                except Exception as e:
                    return np.array([])
            elif str_start_date >= '2015-04-01':
                update_to_date = now
                trading_dates = self.get_trading_dates(start, update_to_date)
                for td in reversed(trading_dates):
                    str_td = get_str_date_from_int(td)
                    ad_filename = order_book_id.replace('.', '-') + '2015-04-01' + str_td + '.csv'
                    if os.path.exists('data/' + ad_filename) and str_end_date <= str_td:
                        df = pd.read_csv('data/' + ad_filename)
                        df = df.loc[df['trade_date'] <= str_end_date]
                        df = df.reset_index(drop=True)
                        break
        else:
            os.mkdir('data')

        if 'df' not in dir():
            try:
                if is_index:
                    # akshare index?
                    pass
                elif is_found:
                    # akshare has no fund info?
                    pass
                else:
                    code = self.convert_code(order_book_id)
                    df = self.ak.stock_hk_daily(symbol=code, adjust="qfq")
                    df = df[df['date'] <= pd.to_datetime(str_end_date)]
                    df = df[df['date'] >= pd.to_datetime(str_start_date)]
                    df.rename(columns={"date": "trade_date", "volume": "vol"}, inplace=True)
                    df = df.reset_index(drop=True)
            except Exception as e:
                print(e)
                return np.array([])

            # A newly order_book_id maybe None here
            if df is None:
                return np.array([])

            # akshare hk daily not support pct_chg
            # df.rename(columns={"pct_chg": "ratio"}, inplace=True)
            df.to_csv('data/' + filename, index=False)

        df = df.sort_index(ascending=True)
        arr = df.to_records()

        return arr

    @lru_cache()
    def get_order_book_id_list(self):
        """获取所有的港股股票代码列表
        """
        cur_dir = os.path.dirname(__file__)
        filepath = os.path.join(cur_dir, "order_book_id_list_hk.csv")
        try:
            info = self.ak.stock_hk_spot()
            selected_column = ['symbol', 'name']
            info[selected_column].to_csv(filepath, index=False)
            order_book_id_list = info['symbol'].tolist()
        except Exception as e:
            if os.path.isfile(filepath):
                order_book_id_list = pd.read_csv(filepath)['symbol'].tolist()
            else:
                raise("No perm to access akshare stock hk spot or order_book_id_list_hk.csv doesn't exist!")
        return order_book_id_list

    @lru_cache(maxsize=4096)
    def symbol(self, order_book_id):
        """获取order_book_id对应的名字
        :param order_book_id str: 股票代码
        :returns: 名字
        :rtype: str
        """
        cur_dir = os.path.dirname(__file__)
        filepath = os.path.join(cur_dir, "order_book_id_list_hk.csv")
        df = pd.read_csv(filepath, dtype={'symbol': str, 'name': str})
        df = df.loc[df['symbol'] == order_book_id].reset_index(drop=True)
        return "{}[{}]".format(order_book_id, df.loc[0, 'name'])
