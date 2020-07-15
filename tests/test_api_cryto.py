#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import numpy as np

from funcat import *


def test_000001():
    from funcat.data.crypto_backend import CryptoBackend
    set_data_backend(CryptoBackend())

    T("20161216")
    S("000001.XSHG")

    print(C)

if __name__ == '__main__':
    test_000001()

