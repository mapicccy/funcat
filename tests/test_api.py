#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import numpy as np
import tushare as ts
import akshare as ak

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


def test_bak_basic():
    pro = ts.pro_api()
    df = pro.bak_basic(trade_date='20230523', fields='trade_date,ts_code,name,industry,pe,area,float_share,total_share,total_assets,liquid_assets,fixed_assets,reserved,reserved_pershare,eps,bvps,pb,list_date,undp,per_undp,rev_yoy,profit_yoy,gpr,npr,holder_num')
    print(df)
    df.to_csv("stock_basic.csv", index=False)


def test_stock_basic():
    pro = ts.pro_api()
    df = pro.query("stock_basic", exchange='', list_status='L', field='ts_code')
    print(df)
    df.to_csv("stock_basic.csv", index=False)


test_000001()
test_bak_basic()
test_stock_basic()


def test_akshare():
    from funcat.data.akshare_backend import AkshareDataBackend
    set_data_backend(AkshareDataBackend())


    T("20230526")
    S("601360.SH")

    print(O, H, L, C, V, R)
    print(MA(C, 5), MA(C, 10), MA(C, 20))


test_akshare()
