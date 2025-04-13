from datetime import datetime
from lumibot.backtesting import YahooDataBacktesting
from lumibot.brokers import Alpaca
from lumibot.strategies import Strategy
from lumibot.traders import Trader
from config import ALPACA_CONFIG

class BuyHold(Strategy):

    def initialize(self):
        self.sleeptime = "1M"

    def before_market_opens(self):
        if self.first_iteration:
            symbol = "TSLA"
            price = self.get_last_price(symbol)
            quantity = float(0 if self.cash is None else self.cash) / price
            order = self.create_order(symbol, quantity, "buy")
            self.submit_order(order)


if __name__ == "__main__":
    trade = True
    if trade:
        broker = Alpaca(ALPACA_CONFIG)
        strategy = BuyHold(broker=broker)
        trader = Trader()
        trader.add_strategy(strategy)
        trader.run_all()
    else:
        start = datetime(2024, 6, 20)
        end = datetime(2024, 6, 24)
        BuyHold.backtest(
            YahooDataBacktesting,
            start,
            end
        )