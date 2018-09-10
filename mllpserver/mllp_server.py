import socketserver
import logging

from time import time

from msg_etl import C4800
from msg_etl.utils import SB, EB, SB_str, EB_str


logger = logging.getLogger('lis_server.mllpserver')


class MLLPHandler(socketserver.BaseRequestHandler):
    """
    Class to handle MLLP-wrapped HL7 v2.5.1 requests from Roche c4800 (currently). Parses lab data from
    correctly formatted received messages and stores in database.
    Will expand to 6800/8800 next.

    A MLLPHandler object is instantiated once per connection to the server.
    """
    def handle(self):
        RECV_SIZE = 512
        data = b''
        buffer = b''
        chunk_count = 1
        msg_len = 0
        recv_start = time()
        recv_end = 0
        
        # RECV until buffer ends with EB
        while True:
            data = self.request.recv(RECV_SIZE)
            if not data:
                break
            while buffer[-2:] != EB:
                if len(data) <= RECV_SIZE:
                    buffer += data
                    chunk_count += 1
                    msg_len += len(data)
                    break
            if buffer[-2:] == EB:
                break
        msg_bytes = buffer
        recv_end = time() - recv_start
        
        logger.info('Message received from: {}, in {} parts, ~{}b each, in {}s'.format(self.client_address,
                                                                                       chunk_count,
                                                                                       msg_len/chunk_count,
                                                                                       recv_end))
        msg_str = msg_bytes.decode().replace('\n', '\r')
        if all([msg_str[0] == SB_str, msg_str[-2:] == EB_str]):
            process_start = time()
            c4800msg = C4800(msg_str[1:-2])
            logger.info('Message from {}:{}: Accepted, processing...'.format(*self.client_address))
            c4800msg.get_instrument_info()
            c4800msg.save_run_info()
            self.request.sendall(c4800msg.ack('AA'))
            logger.debug('ACK sent: {}'.format(c4800msg.ack('AA')))
            logger.info('ACK sent {}s after msg received.'.format(time() - recv_start))
            c4800msg.save_results()
            process_end = time() - process_start
            logger.info('Message from {}:{} processed, saved to database.'.format(*self.client_address))
            logger.info('Msg processed in {}s'.format(process_end))
        else:
            logger.warning('Message from {}:{} - Rejected, incorrect framing.'.format(*self.client_address))
            self.request.sendall(b'msg rejected\nincorrect framing\nclosing connection...\n')


class MLLPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
