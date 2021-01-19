#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import numpy as np

from funcat import *
from funcat.context import ExecutionContext as funcat_execution_context


def test_000001():
    from funcat.data.tencent_backend import TencentDataBackend
    set_data_backend(TencentDataBackend())

    data_backend = funcat_execution_context.get_data_backend()
    order_book_id_list = data_backend.get_order_book_id_list()
    f = funcat_execution_context.get_current_freq()
    print(f)
    funcat_execution_context.set_current_freq("15m")
    f = funcat_execution_context.get_current_freq()
    print(f)

    T("20210119")
    S("601360.SH")

    print(C)

if __name__ == '__main__':
    test_000001()

