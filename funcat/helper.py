# -*- coding: utf-8 -*-
#

from __future__ import print_function

import datetime
import numpy as np
from tqdm import tqdm

from .context import ExecutionContext, set_current_security, set_current_date, symbol, get_current_security
from .utils import getsourcelines, FormulaException, get_int_date


def suppress_numpy_warn(func):
    def wrapper(*args, **kwargs):
        try:
            old_settings = np.seterr(all='ignore')
            return func(*args, **kwargs)
        finally:
            np.seterr(**old_settings)  # reset to default
    return wrapper


def choose(order_book_id, func, callback):
    set_current_security(order_book_id)
    try:
        if func():
            date = ExecutionContext.get_current_date()
            callback(date, order_book_id, symbol(order_book_id))
    except FormulaException as e:
        pass


@suppress_numpy_warn
def select(func, start_date="2019-10-01", end_date=None, callback=print, order_book_id_list=None):
    print(getsourcelines(func))
    start_date = get_int_date(start_date)
    if end_date is None:
        end_date = datetime.date.today()
    end_date = get_int_date(end_date)
    data_backend = ExecutionContext.get_data_backend()
    if not order_book_id_list:
        order_book_id_list = data_backend.get_order_book_id_list()
    trading_dates = data_backend.get_trading_dates(start=start_date, end=end_date)
    for idx, date in enumerate(reversed(trading_dates)):
        if end_date and date > get_int_date(end_date):
            continue
        if date < get_int_date(start_date):
            break
        set_current_date(str(date))
        print("[{}]".format(date))

        order_book_id_list = tqdm(order_book_id_list)
        for order_book_id in order_book_id_list:
            choose(order_book_id, func, callback)
            order_book_id_list.set_description("Processing {}".format(order_book_id))

    print("")

@suppress_numpy_warn
def backtest(func_buy, func_sell, func_update, account, start_date="2016-10-01", end_date=None, callback=print):
    start_date = get_int_date(start_date)
    if end_date is None:
        end_date = datetime.date.today()
    end_date = get_int_date(end_date)
    date_backend = ExecutionContext.get_data_backend()
    trading_dates = date_backend.get_trading_dates(start=start_date, end=end_date)
    for idx, date in enumerate(trading_dates):
        if get_int_date(date) < start_date:
            continue
        if get_int_date(date) > end_date:
            break
        set_current_date(date)
        if account.position_num == 0:
            func_buy(account)
            if account.position_num != 0:
                continue

        if account.position_num != 0:
            func_sell(account)

        func_update(account)

    print('[{}]'.format(account.value))


def zig_helper(series, n):
    i = 0
    start = 0
    rise = 1
    fall = 2
    candidate_i = None
    peers = [0]
    peer_i = 0
    curr_state = start
    z = np.zeros(len(series))
    if len(series) <= n:
        return z, peers
    while True:
        i += 1
        if i == series.size - 1:
            if candidate_i is None:
                peer_i = i
                peers.append(peer_i)
            else:
                if curr_state == rise:
                    if series[n] >= series[candidate_i]:
                        peer_i = i
                        peers.append(peer_i)
                    else:
                        peer_i = candidate_i
                        peers.append(peer_i)
                        peer_i = i
                        peers.append(peer_i)
                elif curr_state == fall:
                    if series[i] <= series[candidate_i]:
                        peer_i = i
                        peers.append(peer_i)
                    else:
                        peer_i = candidate_i
                        peers.append(peer_i)
                        peer_i = i
                        peers.append(peer_i)
            break

        if curr_state == start:
            if series[i] >= series[peer_i] * (1.0 + n / 100.0):
                candidate_i = i
                curr_state = rise
            elif series[i] <= series[peer_i] * (1.0 - n / 100.0):
                candidate_i = i
                curr_state = fall
        elif curr_state == rise:
            if series[i] >= series[candidate_i]:
                candidate_i = i
            elif series[i] <= series[candidate_i] * (1.0 - n / 100.0):
                peer_i = candidate_i
                peers.append(peer_i)
                curr_state = fall
                candidate_i = i
        elif curr_state == fall:
            if series[i] <= series[candidate_i]:
                candidate_i = i
            elif series[i] >= series[candidate_i] * (1.0 + n / 100.0):
                peer_i = candidate_i
                peers.append(peer_i)
                curr_state = rise
                candidate_i = i
    for i in range(len(peers) - 1):

        peer_start_i = peers[i]
        peer_end_i = peers[i + 1]
        start_value = series[peer_start_i]
        end_value = series[peer_end_i]
        a = (end_value - start_value) / (peer_end_i - peer_start_i)
        for j in range(peer_end_i - peer_start_i + 1):
            z[j + peer_start_i] = start_value + a * j

    return z, peers
