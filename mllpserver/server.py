import socketserver
import logging

from config import Config
from database import Database
from message_etl import C4800

# TODO flesh out logging...
logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO,
                    filename='logs/logs.txt')

logger = logging.getLogger('mllpserver')



class MLLPHandler(socketserver.BaseRequestHandler):
    """
    Class to handle MLLP-wrapped HL7 v2.5.1 requests from Roche c4800 (currently). Parses lab data from
    correctly formatted received messages and stores in database.
    Will expand to 6800/8800 next.

    A MLLPHandler object is instantiated once per connection to the server.
    """
    def handle(self):
        self.data = self.request.recv(102400)
        logger.info('Message received from: {}'.format(self.client_address))
        raw = self.data.decode().replace('\n', '\r')
        if all([raw[0] == '\x0b', raw[-2:] == '\x1c\r']):
            c4800msg = C4800(raw[1:-2])
            logger.info('Message from {}: Accepted, processing...'.format(self.client_address))
            print('MSG from {}: Accepted, processing...'.format(self.client_address))
            c4800msg.get_instrument_info()
            c4800msg.get_run_info()
            c4800msg.save_results()
            logger.info('Message from {} processed, saved to database.'.format(self.client_address))
            self.request.sendall(c4800msg.ack('AA'))
            print('MSG processing complete')
        else:
            logger.warning('Message from {}: Rejected, incorrect framing.'.format(self.client_address))
            print('MSG RECV {}: Rejected, incorrect framing'.format(self.client_address))
            self.request.sendall(b'msg rejected\nincorrect framing\nclosing connection...\n')


if __name__ == '__main__':
    logger.info('RDBMS starting...')
    Database.initialize(dsn=Config.DATABASE)
    logger.info('RDBMS initialized...')
    logger.info('Starting MLLPserver...')
    with socketserver.TCPServer(Config.SERVER_ADDR, MLLPHandler) as server:
        logger.info('Server Address: {}'.format(server.server_address))
        try:
            while True:
                server.handle_request()
        except KeyboardInterrupt:
            server.shutdown()
