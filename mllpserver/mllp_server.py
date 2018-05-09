import socketserver
import logging

from message_etl import C4800


logger = logging.getLogger('lis_server.mllpserver')


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
            logger.info('Message from {}:{}: Accepted, processing...'.format(*self.client_address))
            c4800msg.get_instrument_info()
            c4800msg.save_run_info()
            c4800msg.save_results()
            logger.info('Message from {}:{} processed, saved to database.'.format(*self.client_address))
            self.request.sendall(c4800msg.ack('AA'))
        else:
            logger.warning('Message from {}:{} - Rejected, incorrect framing.'.format(*self.client_address))
            print('MSG RECV {}:{} - Rejected, incorrect framing'.format(*self.client_address))
            self.request.sendall(b'msg rejected\nincorrect framing\nclosing connection...\n')


class MLLPServer(socketserver.ThreadingTCPServer):
    pass

# Holdover from testing
# if __name__ == '__main__':
#     logger.debug('RDBMS starting...')
#     Database.initialize(dsn=Config.DATABASE)
#     logger.debug('RDBMS initialized...')
#     logger.debug('Starting MLLPServer...')
#     with socketserver.TCPServer(Config.SERVER_ADDR, MLLPHandler) as server:
#         logger.debug('Server Address: {}'.format(server.server_address))
#         try:
#             while True:
#                 server.handle_request()
#         except KeyboardInterrupt:
#             server.shutdown()
