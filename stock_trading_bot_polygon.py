import alpaca_trade_api as trdeapi
from alpaca_trade_api import StreamConn

import config

class PythonTradingBot:
    def __init__(self):
        self.slpaca = tradeapi.REST(config.APCA_API_KEY, config.APCA_API_SECRET, config.APCA_API_ENDPOINT, api_version="v2")
    def run(self):
        #on each minute
        async def on_minute(conn, channel, bar):
            #Entry
            if bar.close >= bar.open and bar.open -bar.low > 0.1:
                print("Buying on Doji Candle!")
                self.alpaca.submit_order("MSFT", 1, "buy", "market", "day")
            #TODO: Take profit at 1% increase (e.g. 170 take profit at 171.7)    

        #Connect to get streaming stock market data
        self.conn = StreamConn('Polygon Key Here', 'Polygon Key Here', 'wss://alpaca.socket.polygon.io/stocks')
        on_minute = self.conn(r'AM$')(on_minute)
        #Subscibe to Microsoft Stock
        conn.run(['AM.MSFT'])
bd = PythonTradingBot()
bd.run()