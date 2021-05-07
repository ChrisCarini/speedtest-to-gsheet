# `speedtest` to gSheet

## Prerequisites

You will need to install the `speedtest` CLI as provided by Ookla (speedtest.net).

You can find [installation instructions for your platform here](https://www.speedtest.net/apps/cli).

## Setup

### Create Google Sheet

1. Create a new Google Sheet to use
1. Update `speedtest_to_gsheet.py` variable `GSHEET_DOC_KEY` with the document key for your new document.

### Create Service Account

1. Head to https://console.developers.google.com/cloud-resource-manager?pli=1
1. Click `Create Project`
1. Name your project `speedtest-to-gsheet` (or whatever you wish)
1. Click `Create`
1. Follow the steps here to enable `Drive + Sheet API` access -> https://gspread.readthedocs.io/en/latest/oauth2.html#enable-api-access
    1. Under “APIs & Services > Library”, search for “Drive API” and enable it.
    2. Under “APIs & Services > Library”, search for “Sheets API” and enable it.
    3. Enable API Access for a Project if you haven’t done it yet.
    4. Go to “APIs & Services > Credentials” and choose “Create credentials > Service account key”.
    5. Fill out the form
    6. Click “Create key”
    7. Select “JSON” and click “Create”
    8. **Save the file as `speedtest-to-gsheet-service-account-key.json` in the root of this project!!!**
    9. Very important! Go to your spreadsheet and share it with a client_email from the step above. Just like you do with any other Google account. If you don’t do this, you’ll get a gspread.exceptions.SpreadsheetNotFound exception when trying to access this spreadsheet from your application or a script.
