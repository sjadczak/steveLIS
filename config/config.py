import os


class Config:
    ADDRESS = os.getenv('LIMS_ADDR', '0.0.0.0')
    PORT = int(os.getenv('LIMS_PORT', '2575'))
    SERVER_ADDR = (ADDRESS, PORT)

    LABNAME = os.getenv('LABNAME', 'Default Labname')

    DATABASE = os.getenv('DB_URI', 'postgres://limstest:password@localhost:5432/limslite')
