from datetime import datetime

import pandas as pd
from lumibot.backtesting import YahooDataBacktesting
from lumibot.brokers import Alpaca
from lumibot.entities import TradingFee
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader

from config import IS_BACKTESTING, STRATEGY_NAME

"""
Strategy Description

This strategy uses simple momentum to pick the top N ETFs to buy and hold for a given period of time.
The strategy will analyze the total return of each ETF over the analysis period and pick the top N ETFs to hold.
Once the top N ETFs are picked, the strategy will buy and hold them until the next rebalance period,
at which point it will sell the bottom N ETFs and buy the top N ETFs again.

"""


class StockTopETFPicker(Strategy):
  parameters = {
    "symbols": [],  # The list of all symbols we will be analyzing
    "number_of_symbols":
    5,  # The number of symbols we will be holding at any given time
    "analysis_period": 1500,  # The number of days to analyze
    "rebalance_threshold": 0.08,  # The threshold to rebalance the portfolio
  }

  def initialize(self):
    # There is only one trading operation per day
    # No need to sleep between iterations
    self.sleeptime = "1D"

    self.minutes_before_closing = 1

    # self.set_market("24/7")

  def on_trading_iteration(self):
    # Get the parameters
    symbols = self.parameters["symbols"]
    number_of_symbols = self.parameters["number_of_symbols"]
    analysis_period = self.parameters["analysis_period"]
    rebalance_threshold = self.parameters["rebalance_threshold"]

    # Create a dictionary to store the total returns for each symbol
    total_returns = {}

    # Log message
    self.log_message(f"Analyzing {len(symbols)} symbols: {symbols}")

    # Loop through all the symbols
    for symbol in symbols:
      # Get the historical prices for the symbol
      data = self.get_historical_prices(symbol, analysis_period, "day")

      # Check if we got any data
      if data is None:
        # If we didn't get any data, skip this symbol and remove it from the list
        # self.parameters["symbols"].remove(symbol)
        continue

      # Get the dataframe of the historical prices
      df = data.df

      # Check that the dataframe has at least 4.5/7 rows of the analysis_period (64%)
      # This is to make sure we got the right amount of data, after accounting for weekends and holidays
      if len(df) < 4.5 / 7 * analysis_period:
        continue

      # Get the price of the asset
      price = self.get_last_price(symbol)

      # If the price is less than $1, skip this symbol (no penny stocks)
      if price < 1:
        continue

      # Get the total return over the analysis period
      total_return = df["close"].iloc[-1] / df["close"].iloc[0]

      # Store the total return in the dictionary
      total_returns[symbol] = total_return

    # Convert the dictionary to a dataframe
    total_returns_df = pd.DataFrame.from_dict(total_returns,
                                              orient="index",
                                              columns=["total_return"])

    # Sort the dataframe by total return
    total_returns_df = total_returns_df.sort_values(by="total_return",
                                                    ascending=False)

    # Get the top N symbols
    top_symbols = total_returns_df.index[:number_of_symbols]

    # Send a message to Discord with the top_symbols list
    message = f"""
        -----------
        **Current Top {number_of_symbols} ETFs to Hold**
        {top_symbols.to_list()}
        """
    self.log_message(message, broadcast=True)

    # Get all our positions
    positions = self.get_positions()

    # Create a positions dictionary
    positions = {position.symbol: position for position in positions}

    # Get our portfolio value
    portfolio_value = self.get_portfolio_value()

    # Loop through all the positions
    for position in positions.values():
      # Get the symbol of the position
      symbol = position.symbol

      # If we own a position that is not in the top N, sell it
      if symbol not in top_symbols and symbol != "USD":
        # Check that we own at least one share
        if position.quantity < 1:
          continue

        # Sell the position
        order = self.create_order(symbol, position.quantity, "sell")
        self.submit_order(order)

        # Get the current price of the position
        price = self.get_last_price(symbol)

        # Add a marker to our chart for when we sold
        self.add_marker(f"Sell {symbol}",
                        symbol="triangle-down",
                        value=price,
                        color="red")

    # Sleep for 10 seconds to make sure all the orders are filled
    self.sleep(10)

    # Loop through all the top N symbols
    for symbol in top_symbols:
      # If we don't own a position in the top N, buy it
      if symbol not in positions:
        # Calculate the amount we should spend on the asset
        amount_to_spend = portfolio_value / number_of_symbols

        # Calculate the quantity of the asset we can buy
        quantity = amount_to_spend // self.get_last_price(symbol)

        # Get the amount of cash we have
        cash = self.get_cash()

        # If we have enough cash to buy at least one share and we have enough cash to buy the asset, buy it
        if quantity >= 1 and cash >= amount_to_spend:
          order = self.create_order(symbol, quantity, "buy")
          self.submit_order(order)

          # Add a marker to our chart for when we bought
          self.add_marker(
            f"Buy {symbol}",
            symbol="triangle-up",
            value=self.get_last_price(symbol),
            color="green",
          )

      # If we already own a position in the top N, make sure we own the right quantity
      else:
        # Get the current quantity of the position
        quantity = positions[symbol].quantity

        # Calculate the amount we should spend on the asset
        amount_to_spend = portfolio_value / number_of_symbols

        # Calculate the quantity of the asset we should own
        price = self.get_last_price(symbol)
        quantity_should_own = amount_to_spend // price

        # Get the amount of cash we have
        cash = self.get_cash()

        # If we should own more, buy more
        if quantity < quantity_should_own and cash >= amount_to_spend:
          # Calculate the quantity to buy
          quantity_to_buy = quantity_should_own - quantity

          pct_of_portfolio = (quantity_to_buy * price) / portfolio_value

          if pct_of_portfolio > rebalance_threshold:
            # Buy the position
            order = self.create_order(symbol, quantity_to_buy, "buy")
            self.submit_order(order)

            # Add a marker to our chart for when we bought
            self.add_marker(
              f"Buy {symbol}",
              symbol="triangle-up",
              value=self.get_last_price(symbol),
              color="green",
            )

        # If we should own less, sell some
        elif quantity > quantity_should_own:
          # Calculate the quantity to sell
          quantity_to_sell = quantity - quantity_should_own

          pct_of_portfolio = (quantity_to_sell * price) / portfolio_value

          if pct_of_portfolio > rebalance_threshold:
            # Sell the position
            order = self.create_order(symbol, quantity_to_sell, "sell")
            self.submit_order(order)

            # Add a marker to our chart for when we sold
            self.add_marker(
              f"Sell {symbol}",
              symbol="triangle-down",
              value=self.get_last_price(symbol),
              color="red",
            )


def fetch_tickers():
  country_etfs = [
    "SPY",
    "EFA",
    "EWJ",
    "EWG",
    "EWU",
    "EWC",
    "EWZ",
    "EWA",
    "EWW",
    "EWY",
    "EWQ",
    "EWP",
    "EWI",
    "EWT",
    "EWL",
    "EWM",
    "EWS",
    "EWH",
    "EIS",
    "ENZL",
    "EIDO",
    "EPHE",
    "EPU",
    "EZA",
    "ECH",
    "THD",
    "TUR",
    "ERUS",
    "INDA",
    "GREK",
    "EDEN",
    "EWD",
    "NORW",
    "EFNL",
    "EWN",
    "EWK",
    "EIRL",
    "EPOL",
    "PGAL",
    "EWO",
    "EWI",
    "EWP",
    "EWQ",
    "EWG",
    "EWU",
    "GREK",
    "EWI",
  ]

  sector_etfs = [
    "XLK",
    "SMH",
    "GLD",
    "XME",
    "URA",
    "XLF",
    "XLE",
    "XLV",
    "XLY",
    "XLP",
    "XLI",
    "XLRE",
    "XLC",
    "XLB",
    "XTL",
    "XLU",
    "IGV",
    "FDN",
    "IYT",
    "IYR",
    "IHF",
    "ITB",
    "GDX",
    "SIL",
    "KWEB",
    "SOXX",
    "ARKK",
    "ARKG",
    "ARKW",
    "ARKF",
    "ARKQ",
    "CLOU",
    "FIVG",
    "ROBO",
    "ESPO",
    "BOTZ",
    "HACK",
  ]

  leveraged_etfs = [
    "TQQQ",
    "UPRO",
    "UDOW",
    "SPXL",
    "TECL",
    "SOXL",
    "FAS",
    "NUGT",
    "ERX",
    "LABU",
    "YINN",
    "EURL",
    "DUST",
    "SDOW",
    "SPXS",
    "SQQQ",
    "FAZ",
    "SOXS",
    "DRV",
    "EDZ",
    "UVXY",
  ]

  # Return the list of tickers
  return country_etfs + sector_etfs + leveraged_etfs


if __name__ == "__main__":
  # Get a list of all the stocks in the S&P 500 using yfinance
  tickers = fetch_tickers()

  if not IS_BACKTESTING:
    ####
    # Run the strategy live
    ####
    from config import (
      ALPACA_CONFIG,
    )

    trader = Trader()
    broker = Alpaca(ALPACA_CONFIG)

    strategy = StockTopETFPicker(
        broker=broker,
        discord_account_summary_footer=
        "This strategy code is available as part of the [**Starter Plan**](<https://lumiwealth.com/starter-plan/>)\n"
        "If you have the Starter Plan or higher [**Click Here To Run This Strategy**](<https://github.com/Lumiwealth-Strategies/diversified_leverage_with_threshold>)\n"
        "**IMPORTANT:** Access to this algorithm is not automatic. If you get a 404 Error then please contact <@479785401209323535> for us to give you access. Also, make sure you are logged into GitHub.",
        name=STRATEGY_NAME,
        )
    strategy.set_parameters({
      "symbols": tickers,
    })
    trader.add_strategy(strategy)
    trader.run_all()

  else:
    ############################################
    # Backtest the strategy
    ############################################

    ####
    # Configuration Options
    ####

    backtesting_start = datetime(2011, 1, 1)
    backtesting_end = datetime(2024, 6, 26)
    trading_fee = TradingFee(percent_fee=0.001)  # 0.1% fee per trade

    ####
    # Start Backtesting
    ####

    days_to_analyze = [1500] #[1000, 1500, 2000, 2500] #[50, 100, 200, 300]  # [1000, 1500, 2000, 2500]

    for days in days_to_analyze:
      strat = StockTopETFPicker.run_backtest(
        YahooDataBacktesting,
        backtesting_start,
        backtesting_end,
        benchmark_asset="SPY",
        buy_trading_fees=[trading_fee],
        sell_trading_fees=[trading_fee],
        parameters={
          "symbols": tickers,
          "analysis_period": days,
        },
        name=f"Top ETF Picker {days} Days",
        # polygon_api_key=POLYGON_CONFIG["API_KEY"],
        # polygon_has_paid_subscription=True,
      )

      # Export the positions to a CSV file
      positions = strat[1].get_positions()

      # Create records list
      records = []
      for position in positions:
        # Get the last price of the asset
        last_price = strat[1].get_last_price(position.asset.symbol)

        # Create the record
        record = {
          "symbol": position.asset.symbol,
          "quantity": position.quantity,
          "last_price": last_price,
        }

        # Add the record to the list
        records.append(record)

      positions_df = pd.DataFrame.from_records(records)
      positions_df.to_csv("positions.csv", index=False)