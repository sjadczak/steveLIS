import socketserver

from config import Config
from database import Database
from instrument_etl import C4800Message


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
            c4800msg = C4800Message(raw[1:-2])
            print('MSG RECV {}: Accepted, processing...'.format(self.client_address))
            instrument_id = c4800msg.save_instrument_info()
            print('instrument id:', instrument_id)
            assay_info = c4800msg.get_assay_info(instrument_id)
            print('assay_id: ', assay_info)
            run_info = c4800msg.save_run_info(instrument_id)
            print('print run_info:', run_info)
            results = [c4800msg.parse_result(spm, run_info, assay_info.id) for spm in c4800msg.msg.oul_r22_specimen]
            c4800msg.save_results(results)
            self.request.sendall(c4800msg.ack(c4800msg.msg, 'AA'))
        else:
            print('MSG RECV {}: Rejected, incorrect framing'.format(self.client_address))
            self.request.sendall(b'msg rejected\nincorrect framing\nclosing connection...\n')


if __name__ == '__main__':
    Database.initialize(dsn=Config.DATABASE)
    with socketserver.TCPServer(Config.SERVER_ADDR, MLLPHandler) as server:
        server.serve_forever()
