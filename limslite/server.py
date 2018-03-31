import socketserver

from hl7apy.core import Message
from hl7apy.parser import parse_message

from config import Config


def to_mllp(msg):
    """
    Encodes input strings to UTF-8 byte strings, adds MLLP framing characters.
    :param msg: ER7 formatted string input message
    :return: MLLP-framed UTF-8 encoded byte string
    """
    sb = b'\x0B'
    eb = b'\x1C'
    return sb + msg.replace('\n', '\r').encode() + eb + b'\r'


def ack(msg, resp_type='AA'):
    """
    Build ACK response for incoming message.

    :param msg: incoming message as hl7apy message
    :param resp_type: 'AA' for ACK, 'AR' for Reject, 'AE' for NAK
    :return: ACK ('AA','AR','AE') message
    """
    resp_types = ('AA', 'AR', 'AE')
    if resp_type not in resp_types:
        raise ValueError("Invalid ACK type. Expected one of: {}".format(resp_types))
    resp = Message('ACK', version='2.5.1')
    resp.msh.msh_3 = 'LIS'
    resp.msh.msh_4 = 'LIS Facility'
    resp.msh.msh_5 = msg.msh.msh_3
    resp.msh.msh_6 = Config.LABNAME
    resp.msh.msh_9 = 'ACK^R22^ACK'
    resp.msh.msh_10 = msg.msh.msh_10
    resp.msh.msh_11 = 'P'
    resp.msh.msh_18 = 'UNICODE UTF-8'
    resp.msh.msh_21 = 'LAB-29^IHE'
    resp.add_segment('MSA')
    resp.msa.msa_1 = resp_type
    resp.msa.msa_2 = msg.msh.msh_10
    if resp_type != 'AA':
        pass
    end_resp = to_mllp(
        resp.to_er7()
    )
    assert isinstance(end_resp, bytes)
    return end_resp


class MLLPHandler(socketserver.BaseRequestHandler):
    """
    Class to handle MLLP-wrapped HL7 v2.5.1 requests from Roche c4800/c6800/c8800

    A MLLPHandler object is instantiated once per connection to the server.
    """
    def handle(self):
        self.data = self.request.recv(102400)
        raw = self.data.decode().replace('\n', '\r')
        if all([raw[0] == '\x0b', raw[-2] == '\x1c', raw[-1] == '\r']):
            msg = parse_message(raw[1:-2])
            run_info = msg.msh
            print(run_info.to_er7())
            for spm in msg.oul_r22_specimen:
                print(int(float(spm.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[1].obx.obx_5.value[:8])))
                print('----')
            self.request.sendall(ack(msg))
        else:
            print('MSG RECV {}: Rejected, incorrect framing'.format(self.client_address))
            self.request.sendall(b'msg rejected\nincorrect framing\nclosing connection...\n')


if __name__ == '__main__':
    with socketserver.TCPServer(Config.SERVER_ADDR, MLLPHandler) as server:
        server.serve_forever()
