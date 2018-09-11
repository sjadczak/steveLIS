SB = b'\x0B'
EB = b'\x1C\r'

SB_str = SB.decode()
EB_str = EB.decode()


def add_mllp_frame(msg):
    """
    Encodes input strings to UTF-8 byte strings, adds MLLP framing characters.
    :param msg: ER7 formatted string input message
    :return: MLLP-framed UTF-8 encoded byte string
    """
    return SB + msg.replace('\n', '\r').encode() + EB
