import json
import subprocess
from datetime import datetime
from typing import Dict

import gspread
from gspread import Cell
from oauth2client.service_account import ServiceAccountCredentials

GSHEET_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Server: Comcast - San Francisco, CA (id = 1783)
# Server: Spectrum - Los Angeles, CA (id = 16974) - THIS SERVER SEEMS TO HAVE STOPPED ON 2020-12-06 @ 1630PT, switched to the above on 2020-12-31 @ 0200PT
SERVER_ID = "1783"

SPEEDTEST_CLI = f"speedtest --server-id={SERVER_ID} --format=json"

# If your document URL is: https://docs.google.com/spreadsheets/d/1234567890abcdefghijklmnopqrstuvwxyz/edit
# You should enter '1234567890abcdefghijklmnopqrstuvwxyz' below like the example.
GSHEET_DOC_KEY = "1234567890abcdefghijklmnopqrstuvwxyz"

GSHEET_SHEET_NAME = f"Speedtest [server {SERVER_ID}] data"
GSHEETS_SERVICE_KEY_FILENAME = "speedtest-to-gsheet-service-account-key.json"


def get_data() -> Dict:
    print(f"Running command: [{SPEEDTEST_CLI}]")
    output = subprocess.Popen(SPEEDTEST_CLI, shell=True, stdout=subprocess.PIPE)

    jsonS, _ = output.communicate()
    print(f'Got: {jsonS}')

    data = json.loads(jsonS)
    return data


def get_sheet() -> gspread.Worksheet:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(filename=GSHEETS_SERVICE_KEY_FILENAME, scopes=scope)
    docs = gspread.authorize(credentials)
    doc = docs.open_by_key(GSHEET_DOC_KEY)
    return doc.worksheet(GSHEET_SHEET_NAME)


def main() -> None:
    data = get_data()
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
    main()
