#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import numpy as np

from funcat import *


def test_000001():
    from funcat.data.tushare_backend import TushareDataBackend
    set_data_backend(TushareDataBackend())

    T("20220808")
    S("002694.SZ")

    print(O, H, L, C, V)
    print(MA(C, 5), MA(C, 10), MA(C, 20))

test_000001()
