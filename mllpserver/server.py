import socketserver
import logging

from config import Config
from database import Database
from message_etl import C4800

# TODO add logging


class MLLPHandler(socketserver.BaseRequestHandler):
    """
    Class to handle MLLP-wrapped HL7 v2.5.1 requests from Roche c4800 (currently). Parses lab data from
    correctly formatted received messages and stores in database.
    Will expand to 6800/8800 next.

    A MLLPHandler object is instantiated once per connection to the server.
    """
    def handle(self):
        self.data = self.request.recv(102400)
        raw = self.data.decode().replace('\n', '\r')
        if all([raw[0] == '\x0b', raw[-2:] == '\x1c\r']):
            c4800msg = C4800(raw[1:-2])
            print('MSG RECV {}: Accepted, processing...'.format(self.client_address))
            c4800msg.get_instrument_info()
            c4800msg.get_run_info()
            c4800msg.save_results()
            self.request.sendall(c4800msg.ack('AA'))
            print('MSG processing complete')
        else:
            print('MSG RECV {}: Rejected, incorrect framing'.format(self.client_address))
            self.request.sendall(b'msg rejected\nincorrect framing\nclosing connection...\n')


if __name__ == '__main__':
    Database.initialize(dsn=Config.DATABASE)
    with socketserver.TCPServer(Config.SERVER_ADDR, MLLPHandler) as server:
        server.serve_forever()
