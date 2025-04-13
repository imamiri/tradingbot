import math
from datetime import datetime

from lumibot.entities import Asset, TradingFee
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader

from config import IS_BACKTESTING

"""
Strategy Description

This strategy will rebalance a portfolio of crypto assets every X days. The portfolio is defined in the parameters
section of the strategy. The portfolio is a list of assets, each with a symbol, a weight, and a quote asset. The
quote asset is the asset that the symbol is quoted in. For example, if you want to trade BTC/USDT, then the quote
asset is USDT. If you want to trade BTC/USD, then the quote asset is USD. The quote asset is used to calculate
the value of the portfolio. The weight is the percentage of the portfolio that the asset should take up. For example,
if you have 3 assets in your portfolio, each with a weight of 0.33, then each asset will take up 33% of the portfolio.

"""


class CustomETF(Strategy):
    # =====Overloading lifecycle methods=============

    parameters = {
        "portfolio": [
            {
                "asset": Asset(symbol="DOGE", asset_type="crypto"),
                # "quote": Asset(symbol="USDT", asset_type="crypto"),  # Use for Kucoin
                "quote": Asset(symbol="USD", asset_type="forex"),  # For Alpaca/Backtest
                # "weight": 0.31,
                "weight": 0.24,
            },
            {
                "asset": Asset(symbol="IMX", asset_type="crypto"),
                # "quote": Asset(symbol="USDT", asset_type="crypto"),  # Use for Kucoin
                "quote": Asset(symbol="USD", asset_type="forex"),  # For Alpaca/Backtest
                "weight": 0.24,
            },
            {
                "asset": Asset(symbol="DOT", asset_type="crypto"),
                # "quote": Asset(symbol="USDT", asset_type="crypto"),  # Use for Kucoin
                "quote": Asset(symbol="USD", asset_type="forex"),  # For Alpaca/Backtest
                "weight": 0.24,
            },
            {
                "asset": Asset(symbol="MATIC", asset_type="crypto"),
                # "quote": Asset(symbol="USDT", asset_type="crypto"),  # Use for Kucoin
                "quote": Asset(symbol="USD", asset_type="forex"),  # For Alpaca/Backtest
                "weight": 0.24,
            },
        ],
        "rebalance_period": 10,
    }

    def initialize(self):
        self.sleeptime = "1D"
        self.set_market("24/7")

        # Setting the counter
        self.counter = None

    def on_trading_iteration(self):
        # If the target number of minutes (period) has passed, rebalance the portfolio
        if self.counter == self.parameters["rebalance_period"] or self.counter is None:
            self.counter = 0
            self.rebalance_portfolio()
            self.log_message(
                f"Next portfolio rebalancing will be in {self.parameters['rebalance_period']} cycles."
            )
        else:
            self.log_message(
                "Waiting for next rebalance, counter is {self.counter} but should be {self.parameters['rebalance_period']} to rebalance"
            )

        self.counter += 1

    # =============Helper methods===================

    def rebalance_portfolio(self):
        """Rebalance the portfolio and create orders"""
        orders = []
        for asset in self.parameters["portfolio"]:
            # Get all of our variables from portfolio
            asset_to_trade = asset.get("asset")
            weight = asset.get("weight")
            quote = asset.get("quote")
            symbol = asset_to_trade.symbol

            last_price = self.get_last_price(asset_to_trade, quote=quote)

            if last_price is None:
                self.log_message(
                    f"Couldn't get a price for {symbol} self.get_last_price() returned None"
                )
                continue

            self.log_message(
                f"Last price for {symbol} is {last_price:,f}, and our weight is {weight}. Current portfolio value is {self.portfolio_value}"
            )

            # Get how many shares we already own
            # (including orders that haven't been executed yet)
            quantity = self.get_asset_potential_total(asset_to_trade)

            # Calculate how many shares we need to buy or sell
            shares_value = self.portfolio_value * weight
            new_quantity = 0
            if last_price > 0:
                new_quantity = shares_value / last_price
                
            quantity_difference = new_quantity - quantity

            self.log_message(
                f"Currently own {quantity} shares of {symbol} but need {new_quantity}, so the difference is {quantity_difference}"
            )

            # If quantity is positive then buy, if it's negative then sell
            side = ""
            if quantity_difference > 0:
                side = "buy"
            elif quantity_difference < 0:
                side = "sell"

            # Execute the
            # order if necessary
            if side:
                qty = abs(quantity_difference)

                # Trim to 2 decimal places because the API only accepts
                # 2 decimal places for some assets. This could be done better
                # on an asset by asset basis. e.g. for BTC, we want to use 4
                # decimal places at Alpaca, or a 0.0001 increment. See other coins
                # at Alpaca here: https://alpaca.markets/docs/trading/crypto-trading/
                qty_trimmed = math.floor(qty * 100) / 100

                if qty_trimmed > 0:
                    order = self.create_order(
                        asset_to_trade,
                        qty_trimmed,
                        side,
                        quote=quote,
                    )
                    orders.append(order)

        if len(orders) == 0:
            self.log_message("No orders to execute")

        # First sell any assets that are not in the portfolio
        positions = self.get_positions()
        for position in positions:
            if position.asset not in [
                obj["asset"] for obj in self.parameters["portfolio"]
            ]:
                # Check if it's the quote asset
                if position.asset == self.quote_asset:
                    continue

                if position.quantity > 0:
                    order = self.create_order(position.asset, position.quantity, "sell")
                    if not hasattr(order, "quantity") or order.quantity is None:
                        self.log_message(
                            f"Couldn't create a sell order for {position.asset.symbol} because order.quantity is None"
                        )
                        continue
                    self.submit_order(order)

        # Sleep for 5 seconds to make sure the sell orders are filled
        self.sleep(5)

        # Execute sell orders first so that we have the cash to buy the new shares
        for order in orders:
            if order.side == "sell":
                self.submit_order(order)

        # Sleep for 5 seconds to make sure the sell orders are filled
        self.sleep(5)

        # Execute buy orders
        for order in orders:
            if order.side == "buy":
                self.submit_order(order)

                # TODO: Will this work better for Alpaca?
                # self.safe_sleep(5)


###################
# Run Strategy
###################

if __name__ == "__main__":
    if not IS_BACKTESTING:
        ############################################
        # Run the strategy live
        ############################################

        from config import (
            broker,
        )

        trader = Trader()
        strategy = CustomETF(
            broker=broker,
            discord_account_summary_footer=
        "This strategy code is available as part of the [**Starter Plan**](<https://lumiwealth.com/starter-plan/>)\n"
        "If you have the Starter Plan or higher [**Click Here To Run This Strategy**](<https://github.com/Lumiwealth-Strategies/crypto_custom_etf>)\n"
        "**IMPORTANT:** Access to this algorithm is not automatic. If you get a 404 Error then please contact <@479785401209323535> for us to give you access. Also, make sure you are logged into GitHub.",
            )
        trader.add_strategy(strategy)
        trader.run_all()

    else:
        ####
        # Backtest the strategy
        ####
        from lumibot.backtesting import PolygonDataBacktesting

        from config import POLYGON_CONFIG

        # Backtest this strategy
        backtesting_start = datetime(2020, 1, 1)
        backtesting_end = datetime.now()

        # 0.1% fee, loosely based on Kucoin (might actually be lower bc we're trading a lot)
        # https://www.kucoin.com/vip/level
        trading_fee = TradingFee(percent_fee=0.001)
        quote_asset = Asset(symbol="USD", asset_type="forex")

        CustomETF.backtest(
            PolygonDataBacktesting,
            backtesting_start,
            backtesting_end,
            benchmark_asset=Asset(symbol="BTC", asset_type="crypto"),
            quote_asset=quote_asset,
            buy_trading_fees=[trading_fee],
            sell_trading_fees=[trading_fee],
            polygon_api_key=POLYGON_CONFIG["API_KEY"],
            polygon_has_paid_subscription=POLYGON_CONFIG["IS_PAID_SUBSCRIPTION"],
        )