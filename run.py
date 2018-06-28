import threading

from ui_server import app, logger
from mllpserver import MLLPServer, MLLPHandler
from database import Database
from config import Config


if __name__ == '__main__':
    logger.debug('Database connecting...')
    Database.initialize(dsn=Config.DATABASE)
    logger.debug('Database connected...')
    t1 = threading.Thread(target=MLLPServer(Config.SERVER_ADDR, MLLPHandler).serve_forever, name='mllp', daemon=True)
    t2 = threading.Thread(target=app.run, name='lis', daemon=True)
    logger.info('MLLP Server starting...')
    t1.start()
    logger.info('MLLP Server started in thread {}'.format(t1.name))
    logger.info('steveLIS Server starting...')
    t2.start()
    logger.info('steveLIS Server started in thread {}'.format(t2.name))
    t1.join()
    t2.join()
