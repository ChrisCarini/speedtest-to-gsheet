#!/usr/bin/env bash
##
# USAGE:
#   `./copy_to_host.sh pi@192.168.1.202`
##
DEST=$1

scp {./setup_dev.sh,./speedtest_cron.sh,./requirements.txt,./speedtest-to-gsheet-service-account-key.json,./speedtest_to_gsheet.py} ${DEST}:~/

ssh ${DEST} <<EOF
  # Setup the dev environment
  ~/setup_dev.sh

  # Write out current crontab
  crontab -l > mycron

  # replace any existing cron line for speedtest-cron.sh
  sed -i 's/\*\/15 \* \* \* \* \/home\/pi\/speedtest_cron.sh//' mycron

  # remove all newlines from the end of the file
  sed -i -e :a -e '/^\n*$/{\$d;N;};/\n$/ba' mycron

  # echo new cron into cron file
  echo "*/15 * * * * /home/pi/speedtest_cron.sh" >> mycron

  # install new cron file
  crontab mycron
  rm mycron
EOF