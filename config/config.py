import os


class Config:
    ADDRESS = os.getenv('LIMS_ADDR')
    PORT = int(os.getenv('LIMS_PORT'))
    SERVER_ADDR = (ADDRESS, PORT)

    LABNAME = os.getenv('LABNAME')

    DATABASE = os.getenv('DB_URI')
