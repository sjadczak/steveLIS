import csv
import os
import logging

from datetime import datetime
from flask import render_template, request, send_file

from ui_server import app
from database import CursorFromPool


logger = logging.getLogger('lis_server.ui_server')


# wonky global variables
runs = []
runid = None
results = []


@app.route('/')
def index():
    global runs
    with CursorFromPool() as cur:
        cur.execute("SELECT * FROM runs;")
        runs = [run for run in cur.fetchall()]
    return render_template('index.html', run_list=runs, results=None, runid=None)


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
    path = 'downloads/'
    if not os.path.isdir(path):
        os.makedirs(path)
    time = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')
    logger.debug('Opening file to write results to...')
    filename = '{}_run-{}-results.csv'.format(time, runid)
    with open(path+filename, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(('assay', 'instrument_sw', 'sample_role', 'sample_type', 'sample_id', 'result', 'units',
                         'result_status', 'username,', 'flags', 'cntrl_cts', 'comments', 'dwp_id', 'mwp_id',
                         'mwp_position', 'start_ts', 'end_ts'))
        logger.info('Writing results to file({})'.format(filename))
        writer.writerows(results)
    logger.info('Results CSV saved at {}'.format(filename))
    logger.info('Sending {} for download'.format(filename))
    return send_file('../'+path+filename,
                     mimetype='text/csv',
                     attachment_filename=filename,
                     as_attachment=True)
