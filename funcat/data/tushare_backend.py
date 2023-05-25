# -*- coding: utf-8 -*-
#

from cached_property import cached_property

import pandas as pd
import numpy as np
import datetime
import time
import os

from .rt_data_from_tencent import get_runtime_data
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
        pro = self.ts.pro_api()
        try:
            stock_basics = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date').set_index('symbol', drop=True)
        except Exception as e:
            cur_dir = os.path.dirname(__file__)
            filepath = os.path.join(cur_dir, "stock_basic.csv")
            if os.path.isfile(filepath):
                order_book_id_list = self.get_order_book_id_list()
                df = pd.read_csv(filepath)
                df["symbol"] = df.apply(lambda row: row["ts_code"][:6], axis=1)
                stock_basics = df.loc[df["ts_code"].isin(order_book_id_list)].set_index('symbol', drop=True)
            else:
                raise("No perm to access tushare stock basic api or stock_basic.csv doesn't exist")
        return stock_basics


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
                        df = df.loc[df['trade_date'] <= end]
                        df = df.reset_index(drop=True)
                        break
        else:
            os.mkdir('data')

        if 'df' not in dir():
            try:
                if is_index:
                    df = self.ts.pro_bar(ts_code=order_book_id, asset='I', start_date=str_start_date, end_date=str_end_date)
                elif is_found:
                    df = self.ts.pro_bar(ts_code=order_book_id, asset='FD', start_date=str_start_date, end_date=str_end_date)
                else:
                    df = self.ts.pro_bar(ts_code=order_book_id, adj='qfq', start_date=str_start_date, end_date=str_end_date)
            except IOError:
                # tushare has some stricts, just sleep 1 min when encounter IOError.
                time.sleep(60)
                return np.array([])

            # A newly order_book_id maybe None here
            if df is None:
                return np.array([])

            if freq[-1] == "m":
                df["datetime"] = df.apply(
                    lambda row: int(row["trade_date"].split(" ")[0].replace("-", "")) * 1000000 + int(row["trade_date"].split(" ")[1].replace(":", "")) * 100, axis=1)
            elif freq in ("1d", "W", "M"):
                df["datetime"] = df["trade_date"].apply(lambda x: int(x.replace("-", "")) * 1000000)

            # in case the instance of (r, R, RATIO) to get percentage change
            df.rename(columns={"pct_chg": "ratio"}, inplace=True)
            df.to_csv('data/' + filename, index=False)

        if not df.empty and str(df.at[0, 'trade_date']) == str(last_tradeday) and str(end) == now:
            try:
                rt = get_runtime_data(order_book_id)
            except Exception as e:
                rt = None

            if rt is not None and str(rt.at[0, 'trade_date']) == now:
                rt.rename(columns={"pct_chg": "ratio"}, inplace=True)

                # if pre_amount and cur_amount is different, regard the data shoule be updated
                pre_amount = df.at[0, 'amount']
                cur_amount = rt.at[0, 'amount']

                # rt data has already be updated at least once.
                if str(df.at[0, 'trade_date']) == now:
                    df.drop(labels=0, inplace=True)

                df = pd.concat([rt, df], ignore_index=True)

                # keep the persistent data dynamic update.
                if pre_amount != cur_amount:
                    df.to_csv('data/' + filename, index=False)

        df = df.sort_index(ascending=False)
        arr = df.to_records()

        return arr

    @lru_cache()
    def get_order_book_id_list(self):
        """获取所有的股票代码列表
        """
        cur_dir = os.path.dirname(__file__)
        filepath = os.path.join(cur_dir, "order_book_id_list.csv")
        pro = self.ts.pro_api()
        try:
            info = pro.query('stock_basic', exchange='', list_status='L', field='ts_code')
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
        code = self.convert_code(order_book_id)
        return "{}[{}]".format(order_book_id, self.code_name_map.get(code))
