#!/bin/bash
# 현재 날짜를 기준으로 로그 파일명 설정
DATE=$(date +%Y%m%d)
LOG_FILE="main_$DATE.log"
nohup /home/deploy/.pyenv/shims/python3 -u /home/deploy/realmetro/main.py > "$LOG_FILE" &
echo "main.py has been started in the background. Log file: $LOG_FILE"
