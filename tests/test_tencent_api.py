#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import datetime
import numpy as np

from funcat import *
from funcat.context import ExecutionContext as funcat_execution_context


def test_000001():
    from funcat.data.tencent_backend import TencentDataBackend
    set_data_backend(TencentDataBackend(freq='5m'))

    data_backend = funcat_execution_context.get_data_backend()
    order_book_id_list = data_backend.get_order_book_id_list()
    funcat_execution_context.set_current_freq("5m")

    now = datetime.date.today().strftime("%Y%m%d")
    print(now)
    T(now)
    S("601360.SH")

    print(C, CCI(C, H, L))

if __name__ == '__main__':
    test_000001()

