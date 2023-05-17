import json
import logging
import os
import pprint
import signal
import subprocess
import sys

from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import gspread
import yaml

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from gspread import Cell
from oauth2client.service_account import ServiceAccountCredentials

CHECKED_ENVIRONMENT_VARIABLES = [
    'SERVER_ID',
    'GSHEET_DOC_KEY',
    'GSHEET_SHEET_NAME',
    'GSHEETS_SERVICE_KEY_FILENAME',
]

OOKLA_SPEEDTEST_CLI_EULA_FILE = '~/.config/ookla/speedtest-cli.json'

CONFIG_FILE = 'config.yaml'

GSHEET_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

##
# Setup Logging
##
logger = logging.getLogger()
formatter = logging.Formatter(fmt='%(asctime)s - [%(levelname)s] - %(message)s')

stream_handler = logging.StreamHandler(stream=sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

file_handler = RotatingFileHandler('speedtest_to_gsheet.log', backupCount=5, maxBytes=1000000)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.setLevel(logging.INFO)


##
# Helper Methods
##
def get_config_value(key: str, default: str = '') -> str:
    """Get the configuration value for the provided key. If none found, return the default.

    :param key: The configuration key
    :param default: The default value, should no value be set in the configuration
    :return: The configuration value, or 'default' value should one not be set.
    """
    return str(config.get(key, os.environ.get(key, default)))


def run_command(cmd: str, debug: bool = True) -> Tuple[bytes, bytes]:
    """Run the provided command.

    :param cmd: The command to run
    :param debug: Debug flag; if true, send the output stream to the logger debug and error stream to logger error.
    :return: Tuple of the output stream and error stream
    """
    logger.debug(f'Running command: [{cmd}]')
    outstream, errstream = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()
    if debug:
        logger.debug(f'Command output: {outstream}')
        if errstream:
            logger.error(f'Command error: {errstream}')
    return outstream, errstream


def accept_ookla_speedtest_eula() -> None:
    """Accept the OOKLA Speedtest.net EULA."""
    outstream, errstream = run_command(f'speedtest --accept-license', debug=False)
    logger.debug(f'Accept EULA output: {outstream}')
    if errstream:
        logger.error(f'Accept EULA error: {errstream}')


def get_data(server_id: str) -> Dict[str, Union[Dict[str, Any], str]]:
    """Get the data from running `speedtest` CLI.

    :param server_id: The server ID to use during the speedtest.
    :return: The loaded JSON data as a dict
    """
    outstream, errstream = run_command(f'speedtest --server-id={server_id} --format=json')
    data = json.loads(outstream)
    return data


def get_sheet() -> gspread.Worksheet:
    """Get the Google Sheet object."""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive',
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(filename=GSHEETS_SERVICE_KEY_FILENAME, scopes=scope)
    docs = gspread.authorize(credentials)
    doc = docs.open_by_key(GSHEET_DOC_KEY)
    return doc.worksheet(GSHEET_SHEET_NAME)


def job(server_id: str = None) -> None:
    """The main job; will get the data from the provided server id, and update the sheet with a new row.

    :param server_id: The server ID to query
    """
    logger.info('==========================================')
    logger.info('Starting next run...')

    logger.info('Getting data...')
    data = get_data(server_id=server_id)
    dl_bandwidth = data.get('download', {}).get('bandwidth', 0) / 125000
    ul_bandwidth = data.get('upload', {}).get('bandwidth', 0) / 125000
    result_url = data.get('result', {}).get('url', 'Unknown')
    logger.info(f'{dl_bandwidth} Mbps / {ul_bandwidth} Mbps (D/U) --> {result_url}')
    logger.debug('Data:')
    logger.debug(pprint.pformat(data, indent=4))

    # Update gSheet
    sheet = get_sheet()
    next_row = len(sheet.col_values(1)) + 1
    timestamp = datetime.strptime(data['timestamp'], DATE_FORMAT).strftime(GSHEET_DATE_FORMAT)
    cells = [
        Cell(row=next_row, col=1, value=timestamp),  # Timestamp
        Cell(row=next_row, col=2, value=data['isp']),  # ISP
        Cell(row=next_row, col=3, value=data['server']['country']),  # Server Country
        Cell(row=next_row, col=4, value=data['server']['host']),  # Server Host
        Cell(row=next_row, col=5, value=data['server']['id']),  # Server ID
        Cell(row=next_row, col=6, value=data['server']['ip']),  # Server IP
        Cell(row=next_row, col=7, value=data['server']['location']),  # Server Location
        Cell(row=next_row, col=8, value=data['server']['name']),  # Server Name
        Cell(row=next_row, col=9, value=data['server']['port']),  # Server Port
        Cell(row=next_row, col=10, value=data['ping']['jitter']),  # Ping Jitter
        Cell(row=next_row, col=11, value=data['ping']['latency']),  # Ping Latency
        Cell(row=next_row, col=12, value=data['download']['bandwidth']),  # Download Bandwidth (bytes/sec)
        Cell(row=next_row, col=13, value=data['download']['bytes']),  # Download Bytes
        Cell(row=next_row, col=14, value=data['download']['elapsed']),  # Download Elapsed
        Cell(row=next_row, col=15, value=data['upload']['bandwidth']),  # Upload Bandwidth (bytes/sec)
        Cell(row=next_row, col=16, value=data['upload']['bytes']),  # Upload Bytes
        Cell(row=next_row, col=17, value=data['upload']['elapsed']),  # Upload Elapsed
        Cell(row=next_row, col=18, value=data['interface']['externalIp']),  # Interface ExternalIp
        Cell(row=next_row, col=19, value=data['interface']['internalIp']),  # Interface InternalIp
        Cell(row=next_row, col=20, value=data['interface']['isVpn']),  # Interface IsVpn
        Cell(row=next_row, col=21, value=data['interface']['macAddr']),  # Interface MacAddr
        Cell(row=next_row, col=22, value=data['interface']['name']),  # Interface Name
        Cell(row=next_row, col=23, value=data['result']['url']),  # Result URL
        Cell(row=next_row, col=24, value=data['result']['id']),  # Result ID
    ]
    sheet.update_cells(cell_list=cells, value_input_option='USER_ENTERED')


if __name__ == '__main__':
    ##
    # Accept Speedtest.net EULA
    ##
    if not Path(OOKLA_SPEEDTEST_CLI_EULA_FILE).expanduser().exists():
        logger.info('OOKLA Speedtest.net EULA file *NOT* found, automatically accepting EULA...')
        accept_ookla_speedtest_eula()
        logger.info('OOKLA Speedtest.net EULA accepted!')
    else:
        logger.info('OOKLA Speedtest.net EULA file found, proceeding...')

    ##
    # Load Configuration
    ##
    if not Path(CONFIG_FILE).exists():
        logger.critical(f'Config file {CONFIG_FILE} does not exist. Exiting.')
        exit(1)
    logger.info(f'Loading configuration from [{CONFIG_FILE}]...')
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)

    ##
    # Validate Environment Variables
    ##
    DEBUG = get_config_value('DEBUG', 'false').lower() == 'true'
    logger.info(f'DEBUG: {DEBUG}\n')
    logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

    SCHEDULE_INTERVAL = int(get_config_value('SCHEDULE_INTERVAL', default='0'))
    CRON_EXPRESSION = get_config_value('CRON_EXPRESSION')
    SERVER_ID = get_config_value('SERVER_ID')
    GSHEET_DOC_KEY = get_config_value('GSHEET_DOC_KEY')
    GSHEET_SHEET_NAME = get_config_value('GSHEET_SHEET_NAME')
    GSHEETS_SERVICE_KEY_FILENAME = get_config_value('GSHEETS_SERVICE_KEY_FILENAME')

    # Env Var input validation (basic.)
    for envvar_name in CHECKED_ENVIRONMENT_VARIABLES:
        envvar_value = locals()[envvar_name]
        if not envvar_value:
            logger.info('The following environment variable is not set correctly.')
            padding = ' ' * (32 - len(envvar_name))
            logger.info(f'    {envvar_name}:{padding}{envvar_value}')
            logger.info('')
            logger.info('Please check the environment variables and start the container again. Exiting.')
            exit(1)

    # If both are set, exit; we only want one set.
    if not SCHEDULE_INTERVAL and not CRON_EXPRESSION:
        logger.critical('Set either `CRON_EXPRESSION` or `SCHEDULE_INTERVAL`, but not both. Exiting.')
        exit(1)

    ##
    # Display Running Variables
    ##
    logger.debug('Running with the below environment variables:')
    for envvar_name in CHECKED_ENVIRONMENT_VARIABLES:
        envvar_value = locals()[envvar_name]
        padding = ' ' * (32 - len(envvar_name))
        logger.info(f'    {envvar_name}:{padding}{envvar_value}')

    ##
    # Clients
    ##
    logger.info('Creating scheduler...')
    scheduler = BlockingScheduler()

    def gracefully_exit(signum, frame):
        logger.info('Stopping scheduler...')
        scheduler.shutdown()
        logger.info('Scheduler shutdown.')

    logger.info('Adding shutdown signal handlers...')
    signal.signal(signal.SIGINT, gracefully_exit)
    signal.signal(signal.SIGTERM, gracefully_exit)

    if CRON_EXPRESSION:
        logger.info(f'Adding job to run on the following cron schedule: {CRON_EXPRESSION}')
        scheduler.add_job(
            func=lambda: job(server_id=SERVER_ID),
            trigger=CronTrigger.from_crontab(CRON_EXPRESSION),
        )
    elif SCHEDULE_INTERVAL:
        logger.info(f'Adding job to run every {SCHEDULE_INTERVAL} minutes...')
        scheduler.add_job(
            func=lambda: job(server_id=SERVER_ID),
            trigger='interval',
            minutes=SCHEDULE_INTERVAL,
            next_run_time=datetime.now() + timedelta(seconds=1),
        )
    else:
        logger.critical('No schedule information set.')
        logger.critical('Set either `CRON_EXPRESSION` or `SCHEDULE_INTERVAL` and restart the application.')
        exit(1)
    logger.info(f'Starting job [{scheduler}] ...')
    scheduler.start()
