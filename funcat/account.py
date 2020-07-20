# -*- coding: utf-8 -*-


class Account(object):
    def __init__(self, balance):
        self.balance = balance
        self.position_code = ''
        self.position_price = 0.
        self.position_num = 0
        self.update(price=0.)

    def buy(self, code, price, num):
        if self.balance < price * num:
            raise Exception('insufficient account balance')

        self.position_price = price
        self.position_num = num
        self.balance -= price * num
        self.position_code = code

        assert self.balance >= 0
        self.update(price=price)

    def sell(self, code, price, num):
        assert self.position_code == code
        self.position_num -= num

        if self.position_num == 0:
            self.position_price = 0.

        self.balance += price * num
        self.update(price=price)

    def update(self, price):
        self.curr_price = price
        self.value = self.balance + self.curr_price * self.position_num
