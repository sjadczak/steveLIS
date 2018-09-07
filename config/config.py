import os


class Config:
    ADDRESS = os.getenv('LIMS_ADDR', '0.0.0.0')
    PORT = int(os.getenv('LIMS_PORT', '2575'))
    MLLP_ADDR = (ADDRESS, PORT)

    LABNAME = os.getenv('LABNAME', 'ILB/VL-EID')

    DATABASE = os.getenv('DB_URI', 'postgres://admin:vleid2018@localhost:5432/stevelis')
