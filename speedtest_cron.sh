#!/bin/bash

LOG_FILE=speedtest_cron.log

cd /home/pi/

source ./env/bin/activate

date | tee -a ${LOG_FILE}
python3 speedtest_to_gsheet.py | tee -a ${LOG_FILE}
echo "" | tee -a ${LOG_FILE}