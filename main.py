from tinkoff.invest import exceptions
from tinkoff.invest import Client
from tinkoff.invest import Quotation
from tinkoff.invest import OrderDirection, InstrumentIdType, OrderType, PriceType, SecurityTradingStatus
from tinkoff.invest import PortfolioPosition
from tinkoff.invest import ReplaceOrderRequest
from tinkoff.invest.sandbox.client import SandboxClient

import json
import traceback
from time import sleep
from types import NoneType


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
            return self.services.sandbox.open_sandbox_account().account_id
        if len(accounts) == 1:
            return accounts[0].id
    def update_services(self) -> None:
        self.services = SandboxClient(self.token).__enter__()

class Stratagy():
    def __init__(self, _buy_cond, _sell_cond):
        self.buy_condition = _buy_cond
        self.sell_condition = _sell_cond
    def stratagy(self, client : Client, data : DataStorageResponse):
        self.buy_condition(client, data)
        self.sell_condition(client, data)

class TMOS_Stratagy(Stratagy):
    def __init__(self):
        super().__init__(self.buy_condition, self.sell_condition)

    def buy_condition(self, client : Client, data : DataStorageResponse):
        # get data
        orders = data.orders
        position = data.positions
        order_book = data.order_book

        instrument = client.services.instruments.etf_by(id_type = InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                                                        id = position.figi).instrument
        increment = obj_to_scalar(instrument.min_price_increment)
        
        # buy condition and orders
        orders_prices = sorted([obj_to_scalar(order.average_position_price) for order in orders[OrderDirection.ORDER_DIRECTION_BUY]])
        if position.quantity == Quotation(units=0, nano=0) and orders_prices != []:
            if orders_prices[-1] < obj_to_scalar(order_book.bids[0].price):
                for order in orders[OrderDirection.ORDER_DIRECTION_BUY]:
                    client.services.orders.cancel_order(account_id=client.account, order_id=order.order_id)
                orders_prices = []

        n_order2place = 10 - len(orders_prices)

        # start orders price
        if n_order2place == 10:
            order_price = obj_to_scalar(order_book.bids[0].price)
        else:
            order_price = orders_prices[0] - increment

        if obj_to_scalar(position.quantity) % 2 == 0 and obj_to_scalar(position.quantity) != 0 and orders_prices != []: 
            order_price = obj_to_scalar(position.average_position_price_fifo) - increment / 2 - increment * (obj_to_scalar(position.quantity) / 200)
        elif obj_to_scalar(position.quantity) % 1 == 0 and obj_to_scalar(position.quantity) != 0 and orders_prices != []:
            order_price = obj_to_scalar(position.average_position_price_fifo) - increment * (obj_to_scalar(position.quantity) / 200)

        order_price -= order_price % increment 
        
        # place orders
        for _ in range(n_order2place):
            client.services.orders.post_order(account_id = client.account, 
                direction = OrderDirection.ORDER_DIRECTION_BUY,
                order_type = OrderType.ORDER_TYPE_LIMIT,
                price = scalar_to_quotation(order_price),
                figi = 'BBG333333333',
                quantity = 100)
            order_price -= increment

    def sell_condition(self, client : Client, data : DataStorageResponse):
        # get data
        orders = data.orders
        position = data.positions 

        instrument = client.services.instruments.etf_by(id_type = InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                                                        id = position.figi).instrument
        increment = obj_to_scalar(instrument.min_price_increment)
        
        if obj_to_scalar(position.quantity) == 0:
            return
        
        price = (obj_to_scalar(position.average_position_price_fifo) // increment + 1) * increment
        print(price)
        
        if len(orders[OrderDirection.ORDER_DIRECTION_SELL]) == 0:
            pprint(client.services.orders.post_order(account_id = client.account, 
                            figi = 'BBG333333333',
                            direction = OrderDirection.ORDER_DIRECTION_SELL,
                            order_type = OrderType.ORDER_TYPE_LIMIT,
                            price = scalar_to_quotation(price),
                            quantity = int(obj_to_scalar(position.quantity))))
        else:
            sell_order = orders[OrderDirection.ORDER_DIRECTION_SELL][0]
            if (obj_to_scalar(sell_order.average_position_price) // increment + 1) * increment == price or position.quantity == sell_order.lots_requested - sell_order.lots_executed:
                return
            print(f'Position\n\rprice: {position.average_position_price_fifo}\n\rquantity: {obj_to_scalar(position.quantity)}\n\n\rOrder\n\rprice: {price}\n\rquantity: {sell_order.lots_requested - sell_order.lots_executed}\n\rposition')
            request = ReplaceOrderRequest()
            
            request.account_id = client.account
            request.idempotency_key = orders[OrderDirection.ORDER_DIRECTION_SELL][0].order_id
            request.order_id = orders[OrderDirection.ORDER_DIRECTION_SELL][0].order_id
            request.quantity = int(obj_to_scalar(position.quantity))
            request.price = scalar_to_quotation(price)
            request.price_type = PriceType.PRICE_TYPE_CURRENCY

            pprint(client.services.orders.replace_order(request))
    
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
    
    def _update(self, client : Client) -> None: # protected
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
    
    def get_data(self, request : DataStorageRequest):
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
    def run(self):
        bot = telebot.TeleBot(token=self._load_telegram_token())
        while True:
            sleep(2)
            try:
                if self.Client.services.market_data.get_trading_status(figi='BBG333333333').trading_status != SecurityTradingStatus.SECURITY_TRADING_STATUS_NORMAL_TRADING:
                    continue
                self._iter()
                sleep(2)
            except exceptions.RequestError:
                self.Client.update_services()
                continue
            except Exception as e:
                msg = traceback.format_exc()
                print(msg)
                bot.send_message(self._load_telegram_admin(), msg)
                break

    def _iter(self):
        self.DataManager._update(self.Client)
        self.Stratagy.stratagy(self.Client, 
                               self.DataManager.get_data(DataStorageRequest(figi='BBG333333333', 
                                                                            positions=True,
                                                                            orders=True,
                                                                            order_book=True)))
    def _load_token(self):
        with open('./config.json', 'r') as f:
            return json.load(f)['token']
    def _load_telegram_token(self):
        with open('./config.json', 'r') as f:
            return json.load(f)['telegram_token']
    def _load_telegram_admin(self):
        with open('./config.json', 'r') as f:
            return json.load(f)['telegram_admin']

bot = Bot()
bot.run()

# bot.DataManager._update(bot.Client)
# data = bot.DataManager.get_data(DataStorageRequest(figi='BBG333333333', 
#                                                                     positions=True,
#                                                                     orders=True,
#                                                                     order_book=True))
# for order in data.orders[2]:
#     bot.Client.services.orders.cancel_order(account_id=bot.Client.account,
#                                             order_id=order.order_id)
# bot.Client.services.orders.post_order(figi='BBG333333333', 
#                                       quantity=100, 
#                                       order_type=OrderType.ORDER_TYPE_MARKET,
#                                       direction=OrderDirection.ORDER_DIRECTION_SELL,
#                                       account_id=bot.Client.account)