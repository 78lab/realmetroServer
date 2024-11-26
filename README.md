# realmetro backend jobs

크론탭 관리를 위한 주요 명령어:
crontab -e: 크론탭 생성 및 수정3
crontab -l: 현재 등록된 크론탭 목록 조회4
crontab -r: 현재 사용자의 모든 크론탭 삭제

특수 문자:
*: 모든 값
,: 여러 값 지정
-: 범위 지정
/: 간격 지정

# 매분 실행
* * * * * /test/batch.sh

# 매일 오전 3시 30분 실행
30 3 * * * /test/batch.sh

# 30분마다 실행
*/30 * * * * /test/batch.sh