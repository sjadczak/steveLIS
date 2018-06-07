import logging
import threading
import os
import csv

from datetime import datetime
from flask import Flask, render_template, request, send_file

from mllpserver import MLLPServer, MLLPHandler
from database import Database, CursorFromPool
from config import Config


# TODO Flesh out logging throughout app
logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO,
                    filename='../logs/steve_lis.log')

logger = logging.getLogger('lis_server')

app = Flask(__name__)


runs = []
runid = None
results = []


@app.route('/')
def index():
    global runs
    with CursorFromPool() as cur:
        cur.execute("SELECT * FROM runs;")
        runs = [run for run in cur.fetchall()]
    return render_template('index.html', run_list=runs, results=None)


@app.route('/fetch_results', methods=['GET'])
def fetch_results():
    global results
    global runid
    runid = request.args.get('run')
    logger.info('Fetching results for run {}...'.format(runid))
    with CursorFromPool() as cur:
        cur.execute("SELECT * FROM results_file(%s)", (str(runid),))
        results = [result for result in cur.fetchall()]
    logger.info('Run {} results fetched'.format(runid))
    return render_template('index.html', run_list=runs, results=results, runid=runid)


@app.route('/download', methods=['GET'])
def download():
    if not os.path.isdir('tmp/'):
        os.makedirs('tmp/')
    time = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')
    logger.debug('Opening file to write results to...')
    filename = 'tmp/{}_run-{}-results.csv'.format(time, runid)
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(('assay', 'instrument_sw', 'sample_role', 'sample_type', 'sample_id', 'result', 'units',
                         'result_status', 'username,', 'flags', 'cntrl_cts', 'comments', 'dwp_id', 'mwp_id',
                         'mwp_position', 'start_ts', 'end_ts'))
        logger.info('Writing results to file({})'.format(filename))
        writer.writerows(results)
    logger.info('Results CSV saved at {}'.format(filename))
    logger.info('Sending {} for download'.format(filename))
    return send_file(filename,
                     mimetype='text/csv',
                     attachment_filename=filename,
                     as_attachment=True)


if __name__ == '__main__':
    logger.debug('RDBMS starting...')
    Database.initialize(dsn=Config.DATABASE)
    logger.debug('RDBMS initialized...')
    t1 = threading.Thread(target=MLLPServer(Config.SERVER_ADDR, MLLPHandler).serve_forever, name='mllp', daemon=True)
    t2 = threading.Thread(target=app.run, name='lis', daemon=True)
    logger.info('MLLP Server starting...')
    t1.start()
    logger.info('MLLP Server started in thread {}'.format(t1.name))
    logger.info('LIS Server starting...')
    t2.start()
    logger.info('LIS Server started in thread {}'.format(t2.name))
    t1.join()
    t2.join()

