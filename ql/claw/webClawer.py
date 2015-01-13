import datetime
import time
import urllib2
from threading import Thread

from ql.claw.base import BaseClaw
from ql.common.log import LOG
from ql.db import DailyPrice, Symbol
from ql.db import sql_api as db_api


class WebClawer(BaseClaw):
    """
    Claw quote from google finance.
    """
    def __init__(self, symbols, start=None, end=None):
        self.symbols = symbols
        self.start = start
        self.end = end

    def read(self, url, proxy=None):
        try:
            if proxy:
                import socks
                import socket
                socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 7000)
                socket.socket = socks.socksocket
                import urllib2
            req = urllib2.Request(url)
            resp = urllib2.urlopen(req)
            return resp
        except urllib2.URLError, e:
            print e
            return None
        except Exception as e:
            print e
            return None

    def daily_price_url(self, symbol, start, end):
        """
        get daily from yahoo
        http://ichart.finance.yahoo.com/table.csv?s=002222.sz&a=11&b=25&c=2013&d=11&e=29&f=2014
        """
        code = symbol.code+".sz" if symbol.type=="sz_stock" else symbol.code 
        url = "http://ichart.finance.yahoo.com/table.csv?s=%s&a=%s&b=%s&c=%s&d=%s&e=%s&f=%s" % \
            (code, start[1] - 1, start[2], start[0], end[1] - 1, end[2], end[0])
        return url

    def data2obj(self, id, data):
        print id
        price = []
        now = datetime.datetime.now()
        for field in data:
            p = field.strip().split(',')
            o = DailyPrice(id, datetime.datetime.strptime(p[0], '%Y-%m-%d'),
                    p[1], p[2], p[3], p[4], p[5], now)
            price.append(o)
        return price

    def restore(self, prices):
        db_api.insert_prices(prices)

    def _worker(self, symbol):
        url = self.daily_price_url(symbol, self.start, self.end)
        print url
        LOG.debug(url)
        resp = self.read(url)
        if resp is None:
            LOG.error(resp)
            return
        data = resp.readlines()[1:]
        prices = self.data2obj(symbol.id, data)

        self.restore(prices)

    def fetch_save_symbols(self, pools=10):
        counter = 0
        while counter < len(self.symbols):
            size = len(self.symbols) - counter
            if size > pools:
                size = pools
            process_symbols = self.symbols[counter: counter+size]

            threads = []
            for s in process_symbols:
                thread = Thread(name=s, target=self._worker, args=[s])
                thread.daemon = True
                thread.start()

                threads.append(thread)

            for thread in threads:
                thread.join(120)

            counter += size

            # sleep for 3 second to avoid being blocked by google...
            time.sleep(5)
        

def main():
    symbols = db_api.get_symbols()
    start=(2013,12,25)
    end=(2014,12,29)
    c = WebClawer(symbols, start, end)
    url = c.fetch_save_symbols()

if __name__ == '__main__':
    main()
