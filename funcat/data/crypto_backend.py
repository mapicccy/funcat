# -*- coding: utf-8 -*-
#

import numpy as np

from .backend import DataBackend
from ..utils import lru_cache


class CryptoBackend(DataBackend):

    def get_price(self, order_book_id, start, end, freq):
        """
        :param order_book_id: e.g. 000002.XSHE
        :param start: 20160101
        :param end: 20160201
        :returns:
        :rtype: numpy.rec.array
        """
        self.data = np.array([])

        try:
            self.data = np.load('./btc_backend.npy', allow_pickle=True)
        except IOError:
            print("-" * 50)
            print(">>> The input file does not exist or cannot be read")
            print("-" * 50)
            raise

        if len(self.data) != 0:
            dt = np.dtype([('open', np.float64), ('high', np.float64),
                           ('low', np.float64), ('close', np.float64), ('volume', np.float64)])
            rec = np.empty((len(self.data),), dtype=dt)
            for i in range(len(self.data)):
                rec[i] = tuple(self.data[i])

            return rec
        else:
            return np.array([])

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
