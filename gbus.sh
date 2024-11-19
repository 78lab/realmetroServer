#!/bin/bash
# 현재 날짜를 기준으로 로그 파일명 설정
DATE=$(date +%Y%m%d)
LOG_FILE="gbus_test_$DATE.log"
nohup /home/deploy/.pyenv/shims/python3 -u /home/deploy/realmetro/gbus_test.py > "$LOG_FILE" &
echo "gbus_test.py has been started in the background. Log file: $LOG_FILE"