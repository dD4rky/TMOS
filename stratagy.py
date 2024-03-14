from tinkoff.invest import Client
from tinkoff.invest import Quotation
from tinkoff.invest import OrderDirection, InstrumentIdType, OrderType, PriceType
from tinkoff.invest import ReplaceOrderRequest

from dataclasses import dataclass
import asyncio

from interface import *
from utils import *

from types import CoroutineType

@dataclass()
class StratagyConfig():
    GRID_SIZE = 5
    PROFIT_INCREMENT = 1
    LOTS_PER_PT = 100

class Stratagy():
    def __init__(self, _buy_cond, _sell_cond):
        self.buy_condition = _buy_cond
        self.sell_condition = _sell_cond
    async def stratagy(self, client : Client, _update_method : CoroutineType, _data_manager : CoroutineType):
        event_loop = asyncio.get_event_loop()
        update_method = event_loop.create_task(_update_method)
        data_manager = event_loop.create_task(_data_manager)
        

        await update_method
        data = await data_manager
        self.sell_condition(client, data)

        await update_method
        data = await data_manager
        self.buy_condition(client, data)

class TMOS_Stratagy(Stratagy):
    def __init__(self):
        super().__init__(self._buy_condition, self._sell_condition)

    def _buy_condition(self, client : Client, data : DataStorageResponse):
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

        n_order2place = StratagyConfig.GRID_SIZE - len(orders_prices)
        # start orders price
        if n_order2place == StratagyConfig.GRID_SIZE:
            order_price = obj_to_scalar(order_book.bids[0].price)
        else:
            order_price = orders_prices[0] - increment

        if obj_to_scalar(position.quantity) % 2 == 0 and obj_to_scalar(position.quantity) != 0 and orders_prices == []: 
            order_price = obj_to_scalar(position.average_position_price_fifo) - increment / 2 - increment * (obj_to_scalar(position.quantity) / (StratagyConfig.LOTS_PER_PT * 2))
        elif obj_to_scalar(position.quantity) % 2 == 1 and obj_to_scalar(position.quantity) != 0 and orders_prices == []:
            order_price = obj_to_scalar(position.average_position_price_fifo) - increment * (obj_to_scalar(position.quantity) / (StratagyConfig.LOTS_PER_PT * 2))

        if round(order_price % increment, 1) != 0:
            order_price -= order_price % increment
        
        # place orders
        for _ in range(n_order2place):
            client.services.orders.post_order(account_id = client.account, 
                direction = OrderDirection.ORDER_DIRECTION_BUY,
                order_type = OrderType.ORDER_TYPE_LIMIT,
                price = scalar_to_quotation(order_price),
                figi = 'BBG333333333',
                quantity = StratagyConfig.LOTS_PER_PT)
            print('Buy order placed')
            order_price -= increment

    def _sell_condition(self, client : Client, data : DataStorageResponse):
        # get data
        orders = data.orders
        position = data.positions 

        instrument = client.services.instruments.etf_by(id_type = InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                                                        id = position.figi).instrument
        increment = obj_to_scalar(instrument.min_price_increment)
        
        if obj_to_scalar(position.quantity) == 0:
            return
        elif obj_to_scalar(position.quantity) < 0:
            raise Exception('Negative balance')
        price = (obj_to_scalar(position.average_position_price_fifo) // increment + StratagyConfig.PROFIT_INCREMENT) * increment
        if obj_to_scalar(position.average_position_price_fifo) == price:
            price += increment
        print(obj_to_scalar(position.average_position_price_fifo))
        print(price)

        if orders[OrderDirection.ORDER_DIRECTION_SELL] == []:
            client.services.orders.post_order(account_id = client.account, 
                            figi = 'BBG333333333',
                            direction = OrderDirection.ORDER_DIRECTION_SELL,
                            order_type = OrderType.ORDER_TYPE_LIMIT,
                            price = scalar_to_quotation(price),
                            quantity = int(obj_to_scalar(position.quantity)))
            print('Sell order placed')
            return
        sell_order = orders[OrderDirection.ORDER_DIRECTION_SELL][0]

        cond_1 = (obj_to_scalar(sell_order.average_position_price) // increment + StratagyConfig.PROFIT_INCREMENT) * increment
        cond_2 = cond_1 + increment
        if cond_1 != price or cond_2 != price or obj_to_scalar(position.quantity) != sell_order.lots_requested - sell_order.lots_executed:
            return
        client.services.orders.cancel_order(account_id = client.account,
                                            order_id = sell_order.order_id)
        print('Sell order cancled')