from tinkoff.invest import Client
from tinkoff.invest import Quotation, MoneyValue
from tinkoff.invest import OrderDirection, InstrumentIdType, OrderType
from tinkoff.invest import PortfolioPosition
from tinkoff.invest import SecurityTradingStatus
from tinkoff.invest.sandbox.client import SandboxClient

import numpy as np
import pandas as pd

import os
import json
from time import sleep

from pprint import pprint

def _obj_to_scalar(value: MoneyValue | Quotation):
    return value.units + value.nano / 1_000_000_000

def _scalar_to_quotation(value : float):
    return Quotation(units = value // 1, nano = (value % 1) * 1_000_000_000)

class Client(object):
    def __init__(self, token):
        self.token = token
        self.services = SandboxClient(self.token).__enter__()
        self.account = self._accounts()

        positions = self.services.operations.get_portfolio(account_id=self.account).positions

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
        return self.orders
class Stratagy():
    def __init__(self, _buy_cond, _sell_cond):
        self.buy_condition = _buy_cond
        self.sell_condition = _sell_cond
    def stratagy(self, client : Client, orders : Orders):
        self.buy_condition(client, orders)
        self.sell_condition(client, orders)

class TMOS_Stratagy(Stratagy):
    def __init__(self):
        super().__init__(self.buy_condition, self.sell_condition)
    def buy_condition(self, client : Client, orders: Orders):
        # get data
        orders = orders.update_orders(client)
        position = self._get_position(client)
        instrument = client.services.instruments.etf_by(id_type = InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                                                        id = position.figi).instrument
        order_book = client.services.market_data.get_order_book(figi = position.figi,
                                                                depth = 50)
        if position.quantity == Quotation(0,0):
            order_prices = []
            for order in orders[OrderDirection.ORDER_DIRECTION_BUY]:
                order_prices.append = _obj_to_scalar(client.services.orders.get_order_state(account_id = client.account, order_id = order).average_position_price)
            order_prices = sorted(order_prices)
            if len(order_prices) == 0:
                for i in range(10):
                    price = _obj_to_scalar(order_book.bids[0].price) - _obj_to_scalar(instrument.min_price_increment) * i
                    client.services.orders.post_order(account_id = client.account, 
                                                      figi = 'BBG333333333',
                                                      direction = OrderDirection.ORDER_DIRECTION_BUY,
                                                      order_type = OrderType.ORDER_TYPE_LIMIT,
                                                      price = _scalar_to_quotation(price),
                                                      quantity = 10)
            elif len(order_prices) <= 5:
                for i in range(10 - len(order_prices)):
                    price = order_prices[0] - _obj_to_scalar(instrument.min_price_increment) * (i + 1)
                    client.services.orders.post_order(account_id = client.account, 
                                    figi = 'BBG333333333',
                                    direction = OrderDirection.ORDER_DIRECTION_BUY,
                                    order_type = OrderType.ORDER_TYPE_LIMIT,
                                    price = _scalar_to_quotation(price),
                                    quantity = 10)
                    
    def sell_condition(self, client : Client, orders: Orders):
        orders = orders.update_orders(client)
        
        for order in orders:
            client.services.orders.cancel_order(account_id = client.account,
                                                order_id = order)
        position = self._get_position(client)
        instrument = client.services.instruments.share_by(id_type = InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                                                            id = position.figi).instrument
        if _obj_to_scalar(position.quantity) == 0:
            return

        price = _obj_to_scalar(position.average_position_price) + _obj_to_scalar(instrument.min_price_increment)
        client.services.orders.post_order(account_id = client.account, 
                        figi = 'BBG333333333',
                        direction = OrderDirection.ORDER_DIRECTION_SELL,
                        order_type = OrderType.ORDER_TYPE_LIMIT,
                        price = _scalar_to_quotation(price),
                        quantity = _obj_to_scalar(position.quantity))
        
    def _get_position(self, client : Client):
        positions = client.services.operations.get_portfolio(account_id = client.account).positions
        for position in positions:
            if position.figi == 'BBG333333333':
                return position
        return PortfolioPosition(figi = 'BBG333333333',
                                 quantity = Quotation(0,0))
if __name__ == "__main__": 
    # get token
    with open('./config.json', 'r') as f:
        data  = json.load(f)

    os.environ['token'] = data['token']

    client = Client(os.environ['token'])
    orders = Orders(client)
    str_ = TMOS_Stratagy()
    while True:
        if client.services.market_data.get_trading_status(figi='BBG333333333').trading_status == SecurityTradingStatus.SECURITY_TRADING_STATUS_NORMAL_TRADING:
            str_.stratagy(client, orders)
        sleep(0.5)