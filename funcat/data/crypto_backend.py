# -*- coding: utf-8 -*-
#

from cached_property import cached_property

import numpy as np
import pandas as pd
import datetime

from .okex.spot_api import SpotAPI
from pandas.core.frame import DataFrame

from .backend import DataBackend
from ..utils import lru_cache, get_str_date_from_int, get_int_date


class CryptoBackend(DataBackend):
    api_key = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    seceret_key = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    passphrase = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    url = 'wss://real.okex.com:8443/ws/v3'

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
        sp = SpotAPI(self.api_key, self.seceret_key, self.passphrase, use_server_time=True)
        data = sp.get_kline(ts_code, get_str_date_from_int(start)+'T00:00:00.000Z', get_str_date_from_int(end)+'T23:59:59.000Z', freq)
        data = DataFrame(data)
        data.rename(columns={0:'trade_time', 1:'open', 2:'high', 3:'low', 4:'close', 5:'vol'}, inplace=True)
        data = data.sort_index(ascending=False)
        self.data = data.to_records()
        return self.data
        
    """
    def get_price(self, order_book_id, start, end, freq):
        self.data = np.array([])

        try:
            if order_book_id == 'BTC-USDT':
                self.data = pd.read_csv('/home/guanjun/project/confidential_big_project/btc_backend.csv')
            else:
                self.data = pd.read_csv('/home/guanjun/project/confidential_big_project/eth_backend.csv')
        except IOError:
            print("-" * 50)
            print(">>> The input file does not exist or cannot be read")
            print("-" * 50)
            raise

        if len(self.data) != 0:
            return self.data.to_records() 
        else:
            return np.array([])
    """
    def get_order_book_id_list(self):
        """获取所有的股票代码列表
        """
        pass

    def get_trading_dates(self, start, end):
        """获取所有的交易日

        :param start: 20160101
        :param end: 20160201
        """
        pass

    def symbol(self, order_book_id):
        """获取order_book_id对应的名字
        :param order_book_id str: 股票代码
        :returns: 名字
        :rtype: str
        """
        pass
