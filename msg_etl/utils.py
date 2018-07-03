def add_mllp_frame(msg):
    """
    Encodes input strings to UTF-8 byte strings, adds MLLP framing characters.
    :param msg: ER7 formatted string input message
    :return: MLLP-framed UTF-8 encoded byte string
    """
    sb = b'\x0B'
    eb = b'\x1C'
    return sb + msg.replace('\n', '\r').encode() + eb + b'\r'
