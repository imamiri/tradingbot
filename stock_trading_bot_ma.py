from alpaca.trading.client import TradingClient
import alpaca_trade_api as tradeapi

import config
import numpy as np
import time
import logging

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%a, %d %b %Y %H:%M:%S', filename='./tradingapp.log', filemode='w')

pos_held = False
symbol="AAPL"

trading_client = TradingClient(config.API_KEY, config.API_SECRET, paper=True)

#NEW SDK, DOESN'T ALLOW GETTING DATA FROM LAST 15 MINUTES
# bar_req = StockBarsRequest(symbol_or_symbols=[symbol], start=datetime.datetime.now(pytz.utc), timeframe=TimeFrame.Minute)
# client = StockHistoricalDataClient(secret_key=config.SECRET, api_key=config.KEY)
# market_data = client.get_stock_bars(bar_req)
# print(market_data)

api = tradeapi.REST(key_id=config.API_KEY, secret_key=config.API_SECRET)

market_data = api.get_bars(symbol, tradeapi.TimeFrame.Minute).df
#print(market_data.shape[0])

while True:
    # Get close list of the last 5 data points
    if market_data:
        close_list  = market_data.tail(5)['close'].values
        close_list = np.array(close_list, dtype=np.float64) # Convert to numpy array
        ma = np.mean(close_list)
        last_price = close_list[4] # Most recent closing price
        logging.info(market_data)
        # print(close_list)
        logging.info("Moving Average: " + str(ma))
        logging.info("Last Price: " + str(last_price))
        if ma + 1 < last_price and not pos_held: # If MA is more than 10 cents under price, and we haven't already bought
                logging.info("Buy")
                api.submit_order(
                    symbol=symbol,
                    qty=5,
                    side='buy',
                    type='market',
                    time_in_force='gtc'
                )
                pos_held = True
        elif ma - 1 > last_price and pos_held: # If MA is more than 10 cents above price, and we already bought
                logging.info("Sell")
                api.submit_order(
                    symbol=symbol,
                    qty=5,
                    side='sell',
                    type='market',
                    time_in_force='gtc'
                )
                pos_held = False
    time.sleep(300)