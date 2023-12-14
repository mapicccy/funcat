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


class AkshareDataBackend(DataBackend):

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
    def stock_basics(self):
        try:
            stock_basics = self.ak.stock_info_a_code_name().set_index('code', drop=True)
        except Exception as e:
            cur_dir = os.path.dirname(__file__)
            filepath = os.path.join(cur_dir, "stock_basic.csv")
            if os.path.isfile(filepath):
                order_book_id_list = self.get_order_book_id_list()
                df = pd.read_csv(filepath)
                df["code"] = df.apply(lambda row: row["ts_code"][:6], axis=1)
                stock_basics = df.loc[df["ts_code"].isin(order_book_id_list)].set_index('code', drop=True)
            else:
                raise("No perm to access akshare api or stock_basic.csv doesn't exist")
        return stock_basics


    @cached_property
    def code_name_map(self):
        code_name_map = self.stock_basics[["name"]].to_dict()["name"]
        return code_name_map

    @cached_property
    def trading_dates(self):
        now = datetime.date.today()
        df = self.ak.tool_trade_date_hist_sina()
        # trade_date is an instance of datetime
        df = df.loc[df["trade_date"] <= now]
        trading_dates = [get_int_date(date) for date in df['trade_date'].tolist()]
        return sorted(trading_dates)

    def convert_code(self, order_book_id):
        return str(order_book_id).split(".")[0]

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
        is_found = False
        """
        if ((order_book_id.startswith("0") and order_book_id.endswith(".SH")) or
            (order_book_id.startswith("39") and order_book_id.endswith(".SZ"))
            ):
            is_index = True
        is_found = False
        if ((order_book_id.startswith("5") and order_book_id.endswith(".SH")) or
            (order_book_id.startswith("1") and order_book_id.endswith(".SZ"))
            ):
            is_found = True
        """

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
        filename = (str(order_book_id) + '-' + str_start_date + '-' + str_end_date).replace('.', '-') + '.csv'
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
                    ad_filename = (order_book_id + '-' + '2015-04-01' + '-' + str_td).replace('.', '-') + '.csv'
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
                    code = order_book_id[7:].lower() + order_book_id[:7]
                    df = self.ak.stock_zh_a_daily(code)
                    df['trade_date'] = df['date'].apply(lambda x: x.strftime("%Y%m%d"))
                    df = df.loc[df["trade_date"] >= str_start_date & df["trade_date"] <= str_end_date]
                elif is_found:
                    # akshare has no fund info?
                    pass
                else:
                    code = self.convert_code(order_book_id)
                    df = self.ak.stock_zh_a_hist(code, start_date=start, end_date=end, adjust="qfq")
                    df.rename(columns={"日期": "trade_date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "vol", "成交额": "amount", "涨跌幅": "pct_chg", "涨跌额": "change", "换手率": "turn_over"}, inplace=True)
            except Exception as e:
                print(e)
                return np.array([])

            # A newly order_book_id maybe None here
            if df is None:
                return np.array([])

            # in case the instance of (r, R, RATIO) to get percentage change
            df.rename(columns={"pct_chg": "ratio"}, inplace=True)
            df.to_csv('data/' + filename, index=False)

        df = df.sort_index(ascending=True)
        arr = df.to_records()

        return arr

    @lru_cache()
    def get_order_book_id_list(self):
        """获取所有的股票代码列表
        """
        cur_dir = os.path.dirname(__file__)
        filepath = os.path.join(cur_dir, "order_book_id_list.csv")
        try:
            info = self.ak.stock_info_a_code_name()
            info.rename(columns={"code": "ts_code"}, inplace=True)
            info.to_csv(filepath, index=False)
            order_book_id_list = info['ts_code'].tolist()
        except Exception as e:
            if os.path.isfile(filepath):
                order_book_id_list = pd.read_csv(filepath)['ts_code'].tolist()
            else:
                raise("No perm to access tushare stock basic or order_book_id_list.csv doesn't exist!")
        return order_book_id_list

    @lru_cache(maxsize=4096)
    def symbol(self, order_book_id):
        """获取order_book_id对应的名字
        :param order_book_id str: 股票代码
        :returns: 名字
        :rtype: str
        """
        cur_dir = os.path.dirname(__file__)
        filepath = os.path.join(cur_dir, "order_book_id_list.csv")
        df = pd.read_csv(filepath, dtype={'ts_code': str, 'name': str})
        df = df.loc[df['ts_code'] == order_book_id].reset_index(drop=True)
        return "{}[{}]".format(order_book_id, df.loc[0, 'name'])
