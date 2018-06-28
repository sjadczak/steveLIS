import logging

from flask import Flask


# TODO Flesh out logging throughout app
logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO,
                    filename='logs/steveLIS.log')

logger = logging.getLogger('lis_server')


app = Flask(__name__)

from ui_server import ui_routes
