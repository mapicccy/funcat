#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import numpy as np
import tushare as ts

from funcat import *


def test_000001():
    from funcat.data.tushare_backend import TushareDataBackend
    set_data_backend(TushareDataBackend())


    df = ts.pro_bar(ts_code='000001.SH', asset="I", start_date='20220801', end_date='20220810')
    print(df)

    T("20220810")
    S("000001.SH")

    print(O, H, L, C, V, P, R)
    print(MA(C, 5), MA(C, 10), MA(C, 20))

test_000001()
