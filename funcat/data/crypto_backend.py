# -*- coding: utf-8 -*-
#

from cached_property import cached_property

import numpy as np
import pandas as pd
import datetime
import time
import os

from .okex.spot_api import SpotAPI
from pandas.core.frame import DataFrame

from .backend import DataBackend
from ..utils import lru_cache, get_str_date_from_int, get_int_date


class CryptoBackend(DataBackend):
    def __init__(self, api_key, seceret_key, passphrase, freq, url='wss://real.okex.com:8443/ws/v3'):
        self.api_key = api_key
        self.seceret_key = seceret_key
        self.passphrase = passphrase
        self.freq = int(freq)

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

    @lru_cache(maxsize=4096)
    def get_price(self, ts_code, start, end, freq):
        tmp_end = end
        if len(str(start)) == 14:
            start = datetime.datetime.strptime(str(start), "%Y%m%d%H%M%S").strftime("%Y-%m-%dT%H:%M:%S")
        else:
            start = get_str_date_from_int(start)+'T00:00:00'

        if len(str(end)) == 14:
            end = datetime.datetime.strptime(str(end), "%Y%m%d%H%M%S").strftime("%Y-%m-%dT%H:%M:%S")
        else:
            end = get_str_date_from_int(end)+'T23:59:59'

        nt = datetime.datetime.now().strftime('%Y-%m-%d') + 'T23:59:59'
        filename = ts_code + '-' + freq + '-' + end + '.csv'
        update_to_date = ts_code + '-' + freq + '-' + nt + '.csv'
        if os.path.isfile(update_to_date) and end <= nt:
            data = pd.read_csv(update_to_date)
            data = data.loc[data['datetime'] <= tmp_end]
            self.data = data.to_records()
            return self.data

        sp = SpotAPI(self.api_key, self.seceret_key, self.passphrase, use_server_time=True)
        data0 = sp.get_kline(ts_code, start+'.000Z', end+'.000Z', freq)

        data0 = DataFrame(data0)
        pd_list = [data0]
        for i in range(5):
            e1 = (datetime.datetime.strptime(data0.iloc[-1, 0].replace('T', ' ')[:-5], '%Y-%m-%d %H:%M:%S') + datetime.timedelta(seconds=-int(freq))).strftime('%Y-%m-%dT%H:%M:%S')
            data1 = sp.get_kline(ts_code, start+'.000Z', e1+'.000Z', freq)
            data1 = DataFrame(data1)
            data1.reset_index(drop=True, inplace=True)
            pd_list.append(data1)
            data0 = data1
        
        data = pd.concat(pd_list, axis=0, ignore_index=True)
        data.rename(columns={0:'trade_time', 1:'open', 2:'high', 3:'low', 4:'close', 5:'vol'}, inplace=True)
        data = data.sort_index(ascending=False)

        if freq != '86400':
            data["datetime"] = data.apply(
                    lambda row: int(row['trade_time'].replace("T", " ").split(" ")[0].replace("-", "")) * 1000000 + int(row["trade_time"].replace("T", " ").split(" ")[1][:-5].replace(":", "")), axis=1)
        else:
            data["datetime"] = data["trade_time"].apply(lambda x: int(x.replace("T", " ").split(" ")[0].replace("-", "")) * 1000000)

        data.to_csv(update_to_date, index=False)
        self.data = data.to_records()
        return self.data
        
    def get_order_book_id_list(self):
        """获取所有的股票代码列表
        """
        pass

    def get_trading_dates(self, start, end):
        """获取所有的交易日

        :param start: 20160101
        :param end: 20160201
        """
        if len(str(end)) == 14:
            start = datetime.datetime.strptime(str(end), "%Y%m%d%H%M%S") + datetime.timedelta(seconds=-self.freq*200)
            end = datetime.datetime.strptime(str(end), "%Y%m%d%H%M%S")
        else:
            end = get_str_date_from_int(end)+'T23:59:59'

        date_list = []
        be = start.strftime("%Y%m%d%H%M%S")
        en = end.strftime("%Y%m%d%H%M%S")
        while be <= en:
            date_list.append(int(be))
            be = datetime.datetime.strptime(str(be), "%Y%m%d%H%M%S") + datetime.timedelta(seconds=self.freq)
            be = be.strftime("%Y%m%d%H%M%S")

        return date_list


    def symbol(self, order_book_id):
        """获取order_book_id对应的名字
        :param order_book_id str: 股票代码
        :returns: 名字
        :rtype: str
        """
        pass
