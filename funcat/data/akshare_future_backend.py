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


class AkshareFutureDataBackend(DataBackend):

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
        cur_dir = os.path.dirname(__file__)
        filepath = os.path.join(cur_dir, "future_basic.csv")
        try:
            temp = self.ak.futures_symbol_mark()
            stock_basics = pd.DataFrame()
            for item in temp['symbol']:
                futures_zh_realtime_df = self.ak.futures_zh_realtime(symbol=item)
                stock_basics = pd.concat([stock_basics, futures_zh_realtime_df], ignore_index=True)

            stock_basics.rename(columns={"symbol": "ts_code"}, inplace=True)
            stock_basics.to_csv(filepath, index=False)
        except Exception as e:
            if os.path.isfile(filepath):
                order_book_id_list = self.get_order_book_id_list()
                df = pd.read_csv(filepath)
                df["code"] = df.apply(lambda row: row["ts_code"], axis=1)
                stock_basics = df.loc[df["ts_code"].isin(order_book_id_list)].set_index('code', drop=True)
            else:
                raise("No perm to access akshare api or future_basic.csv doesn't exist")
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
        :param order_book_id: e.g. FG2409
        :param start: 20190101
        :param end: 20190201
        :freq: frequency, only support 2 hours
        :returns:
        :rtype: numpy.rec.array
        """
        is_index = False
        is_found = False

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
                        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
                        df = df[df['trade_date'] <= pd.Timestamp(str_end_date).date()]
                        df = df.reset_index(drop=True)
                        break
        else:
            os.mkdir('data')

        if 'df' not in dir():
            try:
                code = self.convert_code(order_book_id).upper()
                df = self.ak.futures_zh_minute_sina(symbol=code, period=120)
                df.rename(columns={"datetime": "trade_date", "volume": "vol", "成交额": "amount"}, inplace=True)
            except Exception as e:
                print("There was an error fetching futures market data, possibly due to rate limiting. Sleep 5 minutes and try again later.")
                time.sleep(280)
                return np.array([])

            # A newly order_book_id maybe None here
            if df is None:
                return np.array([])

            df = df.loc[df['trade_date'] <= str_end_date]
            df["datetime"] = df.apply(
                lambda row: int(row["trade_date"].split(" ")[0].replace("-", "")) * 1000000 + int(row["trade_date"].split(" ")[1].replace(":", "")), axis=1)

            df.to_csv('data/' + filename, index=False)

        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
        df = df[df['trade_date'] <= pd.Timestamp(str_end_date).date()]
        df = df.sort_index(ascending=True)
        arr = df.to_records()
        return arr

    @lru_cache()
    def get_order_book_id_list(self):
        """获取所有的期货代码列表
        """
        cur_dir = os.path.dirname(__file__)
        filepath = os.path.join(cur_dir, "order_book_id_list_future.csv")
        try:
            temp = self.ak.futures_symbol_mark()
            info = pd.DataFrame()
            for item in temp['symbol']:
                futures_zh_realtime_df = self.ak.futures_zh_realtime(symbol=item)
                info = pd.concat([info, futures_zh_realtime_df], ignore_index=True)

            info.rename(columns={"symbol": "ts_code"}, inplace=True)
            info.to_csv(filepath, index=False)
            order_book_id_list = info['ts_code'].tolist()
        except Exception as e:
            if os.path.isfile(filepath):
                order_book_id_list = pd.read_csv(filepath)['ts_code'].tolist()
            else:
                raise("No perm to access tushare stock basic or order_book_id_list_future.csv doesn't exist!")
        return order_book_id_list

    @lru_cache(maxsize=4096)
    def symbol(self, order_book_id):
        """获取order_book_id对应的名字
        :param order_book_id str: 期货代码
        :returns: 名字
        :rtype: str
        """
        cur_dir = os.path.dirname(__file__)
        filepath = os.path.join(cur_dir, "order_book_id_list_future.csv")
        df = pd.read_csv(filepath, dtype={'ts_code': str, 'name': str})
        df = df.loc[df['ts_code'] == order_book_id].reset_index(drop=True)
        return "{}[{}]".format(order_book_id, df.loc[0, 'name'])
