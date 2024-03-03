from tinkoff.invest import Client
from tinkoff.invest import Quotation, MoneyValue
from tinkoff.invest import OrderDirection # ...
from tinkoff.invest.sandbox.client import SandboxClient

import numpy as np
import pandas as pd

import os
import json

from pprint import pprint

class Client(object):
    def __init__(self, token):
        self.token = token
        self.services = SandboxClient(self.token).__enter__()
        self.account = self._accounts()

        positions = self.services.operations.get_portfolio(account_id=self.account).positions
        pprint(positions)

    def _accounts(self):
        accounts = self.services.users.get_accounts().accounts
        if accounts == []:
            return self.services.sandbox.open_sandbox_account().account_id
        if len(accounts) == 1:
            return accounts[0].id

class Orders():
    orders = {OrderDirection.ORDER_DIRECTION_BUY : [],
              OrderDirection.ORDER_DIRECTION_SELL : []}
    
    def __init__(self, client : Client):
        self.update_orders(client)

    def update_orders(self, client : Client):
        self.orders[OrderDirection.ORDER_DIRECTION_BUY] = []
        self.orders[OrderDirection.ORDER_DIRECTION_SELL] = []

        orders = client.services.orders.get_orders(account_id = client.account).orders
        for order in orders:
            if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
                self.orders[OrderDirection.ORDER_DIRECTION_BUY].append(order.order_id)
            if order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                self.orders[OrderDirection.ORDER_DIRECTION_SELL].append(order.order_id)

class Stratagy():
    def __init__(self, _buy_cond, _sell_cond):
        self.buy_condition = _buy_cond
        self.sell_condition = _sell_cond

class TMOS_Stratagy(Stratagy):
    def __init__(self):
        super().__init__(self.buy_condition, self.sell_condition)
    def buy_condition(self, client : Client, orders: Orders):
        orders = orders.update_orders(client)
        position = self._get_position(client)
    def sell_condition(self, client : Client, orders: Orders):
        ...

    def _get_position(self, client : Client):
        positions = client.services.operations.get_portfolio().positions
        for position in positions:
            if position.figi == 'BBG333333333':
                return position
        return None
if __name__ == "__main__": 
    # get token
    with open('./config.json', 'r') as f:
        data  = json.load(f)

    os.environ['token'] = data['token']

    clinet = Client(os.environ['token'])