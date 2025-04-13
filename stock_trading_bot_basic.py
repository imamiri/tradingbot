from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.stream import TradingStream

import config

trading_client = TradingClient(config.API_KEY, config.API_SECRET, paper=True)
# account = dict(trading_client.get_account())
# for k, v in account.items():
#     print(f"{k}{v}")

order_details = MarketOrderRequest(symbol="AAPL", 
                                   qty=10, 
                                   side=OrderSide.BUY, 
                                   time_in_force=TimeInForce.DAY)
order = trading_client.submit_order(order_data=order_details)

trades = TradingStream(config.API_KEY,
                       config.API_SECRET,
                       paper=True)

async def trade_status(data):
    print(data)

trades.subscribe_trade_updates(trade_status)
trades.run()
