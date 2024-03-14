from tinkoff.invest import exceptions
from tinkoff.invest import Client
from tinkoff.invest import Quotation
from tinkoff.invest import OrderDirection, SecurityTradingStatus
from tinkoff.invest import PortfolioPosition, OrderType
from tinkoff.invest.sandbox.client import SandboxClient

from stratagy import TMOS_Stratagy

import json
import traceback
from time import sleep
from types import NoneType
import asyncio

from pprint import pprint

from interface import *
from utils import *

import telebot



class Client(object):
    def __init__(self, token):
        self.token = token
        self.services = SandboxClient(self.token).__enter__()
        self.account = self._accounts()


    def _accounts(self):
        accounts = self.services.users.get_accounts().accounts
        if accounts == []:
            account_id = self.services.sandbox.open_sandbox_account().account_id
            self.services.sandbox.sandbox_pay_in(account_id=account_id, amount=MoneyValue(currency='RUB', units=10000, nano=0))
            return 
        if len(accounts) == 1:
            return accounts[0].id
    def update_services(self) -> None:
        self.services = SandboxClient(self.token).__enter__()

class DataManager():
    def __init__(self,
                 positions_state : bool = False,
                 orders_state : bool = False,
                 order_book : None | list = None):
        
        self.positions_state = positions_state

        self.orders_state = orders_state

        self.order_book = {}
        if isinstance(order_book, NoneType):
            return
        for or_b in order_book:
            self.order_book[or_b] = None

    def update(self, client : Client) -> DataStorageResponse:
        self._update(client)
        return DataStorageResponse(self.positions, self.orders, self.order_book)
    
    async def _update(self, client : Client) -> None: # protected
        if self.orders_state:
            self.orders = {OrderDirection.ORDER_DIRECTION_BUY : [],
                           OrderDirection.ORDER_DIRECTION_SELL : []}
            orders = client.services.orders.get_orders(account_id = client.account).orders
            for order in orders:
                if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
                    self.orders[OrderDirection.ORDER_DIRECTION_BUY].append(order)
                if order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                    self.orders[OrderDirection.ORDER_DIRECTION_SELL].append(order)

        if self.positions_state:
            self.positions = client.services.operations.get_portfolio(account_id=client.account).positions

        for or_b in self.order_book.keys():
            self.order_book[or_b] = client.services.market_data.get_order_book(figi = or_b,
                                                                    depth = 50)
    
    async def get_data(self, request : DataStorageRequest):
        # get position
        if request.positions:
            for pos in self.positions:
                if pos.figi != request.figi:
                    continue
                positions = pos
                break
            else:
                positions = PortfolioPosition(figi=request.figi,
                                              quantity=Quotation(units=0, nano=0))
        # get orders
        if request.orders:
            orders = {OrderDirection.ORDER_DIRECTION_BUY : [],
                      OrderDirection.ORDER_DIRECTION_SELL : []}
            for order in self.orders[OrderDirection.ORDER_DIRECTION_BUY]:
                if order.figi == request.figi:
                    orders[OrderDirection.ORDER_DIRECTION_BUY].append(order)
            for order in self.orders[OrderDirection.ORDER_DIRECTION_SELL]:
                if order.figi == request.figi:
                    orders[OrderDirection.ORDER_DIRECTION_SELL].append(order)
        # get order book
        if request.order_book:
            order_book = self.order_book[request.figi]
        return DataStorageResponse(positions=positions, orders=orders, order_book=order_book)
    
    def add_order_book(self, order_book : list | str):
        if isinstance(order_book, list):
            for or_b in order_book:
                if or_b in self.order_book.keys():
                    continue
                self.order_book[or_b] = None
        if or_b not in self.order_book.keys():
            self.order_book[or_b] = None

    def remove_order_book(self, order_book : list | str):
        if isinstance(order_book, list):
            for or_b in order_book:
                if or_b not in self.order_book.keys():
                    continue
                del self.order_book[or_b]
        if or_b in self.order_book.keys():
            del self.order_book[or_b] 

class Bot():
    def __init__(self):
        token = self._load_token()
        self.Client = Client(token)
        self.Stratagy = TMOS_Stratagy()
        self.DataManager = DataManager(positions_state = True, orders_state = True, order_book = ['BBG333333333'])

        pprint(self.Client.services.operations.get_portfolio(account_id=self.Client.account).positions)
    async def run(self):
        bot = telebot.TeleBot(token=self._load_telegram_token())
        while True:
            sleep(2)
            try:
                if self.Client.services.market_data.get_trading_status(figi='BBG333333333').trading_status != SecurityTradingStatus.SECURITY_TRADING_STATUS_NORMAL_TRADING:
                    continue
                _iter = self._iter()
                await _iter
                sleep(2)
            except exceptions.RequestError:
                self.Client.update_services()
                msg = traceback.format_exc()
                if 'resource exhausted' in msg:
                    continue
                elif 'order not found' in msg:
                    continue
                elif 'Stream removed' in msg:
                    continue
                elif 'internal error' in msg:
                    continue
                print(msg)
                bot.send_message(self._load_telegram_admin(), msg)
                break

            except Exception as e:
                msg = traceback.format_exc()
                print(msg)
                bot.send_message(self._load_telegram_admin(), msg)
                break

    async def _iter(self):
        update_method = self.DataManager._update(self.Client)
        data_manager = self.DataManager.get_data(DataStorageRequest(figi='BBG333333333', 
                                                    positions=True,
                                                    orders=True,
                                                    order_book=True))
        # self.Stratagy.stratagy(self.Client, 
        #                        self.DataManager.get_data(DataStorageRequest(figi='BBG333333333', 
        #                                                                     positions=True,
        #                                                                     orders=True,
        #                                                                     order_book=True)))
        await self.Stratagy.stratagy(self.Client, update_method, data_manager)
    def _load_token(self):
        with open('./config.json', 'r') as f:
            return json.load(f)['token']
    def _load_telegram_token(self):
        with open('./config.json', 'r') as f:
            return json.load(f)['telegram_token']
    def _load_telegram_admin(self):
        with open('./config.json', 'r') as f:
            return json.load(f)['telegram_admin']

if __name__ == '__main__':
    bot = Bot()
    ev_loop = asyncio.get_event_loop()
    ev_loop.run_until_complete(bot.run())
    
# bot.Client.services.sandbox.close_sandbox_account(account_id=bot.Client.account)


# bot.DataManager._update(bot.Client)
# data = bot.DataManager.get_data(DataStorageRequest(figi='BBG333333333', 
#                                                                     positions=True,
#                                                                     orders=True,
#                                                                     order_book=True))
# for order in data.orders[2]:
#     bot.Client.services.orders.cancel_order(account_id=bot.Client.account,
#                                             order_id=order.order_id)
# bot.Client.services.orders.post_order(figi='BBG333333333', 
#                                       quantity=200, 
#                                       order_type=OrderType.ORDER_TYPE_MARKET,
#                                       direction=OrderDirection.ORDER_DIRECTION_BUY,
#                                       account_id=bot.Client.account)