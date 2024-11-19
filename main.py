import time
import requests
import aiohttp
import asyncio
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

ONESIGNAL_APP_ID = os.getenv("ONESIGNAL_APP_ID") # '6799258c-2608-40ae-ae58-9ab570921e4b'
ONESIGNAL_API_KEY = os.getenv("ONESIGNAL_API_KEY") # 'MDc5YzU2ZmQtODY3Zi00YjMwLThmODgtNDg3OGQ1NTllN2Rj'
SEOUL_API_KEY = os.getenv("SEOUL_API_KEY") # "53797461466e65723730665567764a"  #'486a4d6c796e6572383276786c626a'

ONESIGNAL_URL = 'https://onesignal.com/api/v1/notifications'
REALMETRO_BASE_URL = 'http://swopenapi.seoul.go.kr'

# existing_notification_id = None
# ios_notification_id = None
# stationId = "1008000818"
stationIds = ["1008000818", "1008000804", "1008000805"]
stationName = "문정" # 문정
# upDown = "1"  # 상행
# realtimePositions = []
# arrivalList = []
# pushMsg = ""
# pushMsgTitle = "문정역(별내행 - 가락시장방면) 도착 정보 15:15:06"
# pushMsgBody = '''열차(8178) 장지 도착 (1전역)\n : 1분 30초 후 문정 도착 예정
# 열차(8180) 남한산성입구 도착 (5전역)\n : 5분 34초 후 문정 도착 예정

# 남한산성입구(🚆8180) ➔ 산성 ➔ 남위례 ➔ 복정 ➔ 장지(🚆8178) ➔ 문정'''

# 역과 관련된 정보
station_names = [
    "별내", "다산", "동구릉", "구리", "장자호수공원",
    "암사역사공원", "암사", "천호(풍납토성)", "강동구청",
    "몽촌토성(평화의문)", "잠실", "석촌", "송파",
    "가락시장", "문정", "장지", "복정", "남위례",
    "산성", "남한산성입구(성남법원,검찰청)", "단대오거리", 
    "신흥", "수진", "모란"
]

station_times = [
    {"id": "1008000804", "name": "별내", "timeToNext": 0},   # 초 단위
    {"id": "1008000805", "name": "다산", "timeToNext": 60},   # 초 단위
    {"id": "1008000806", "name": "동구릉", "timeToNext": 60},   # 초 단위
    { "id": "1008000807", "name": "구리", "timeToNext": 60 },   # 초 단위
    { "id": "1008000808", "name": "장자호수공원", "timeToNext": 60 },   # 초 단위
    { "id": "1008000809", "name": "암사역사공원", "timeToNext": 60 },   # 초 단위
    { "id": "1008000810", "name": "암사", "timeToNext": 60 },   # 초 단위
    { "id": "1008000811", "name": "천호(풍납토성)", "timeToNext": 60 },   # 초 단위
    { "id": "1008000812", "name": "강동구청", "timeToNext": 60 },   # 초 단위
    { "id": "1008000813", "name": "몽촌토성(평화의문)", "timeToNext": 60 },   # 초 단위
    { "id": "1008000814", "name": "잠실", "timeToNext": 60 },   # 초 단위
    { "id": "1008000815", "name": "석촌", "timeToNext": 60 },   # 초 단위
    { "id": "1008000816", "name": "송파", "timeToNext": 60 },   # 초 단위
    { "id": "1008000817", "name": "가락시장", "timeToNext": 60 },   # 초 단위
    { "id": "1008000818", "name": "문정", "timeToNext": 60 },   # 초 단위
    { "id": "1008000819", "name": "장지", "timeToNext": 60 },   # 초 단위
    { "id": "1008000820", "name": "복정", "timeToNext": 60 },   # 초 단위
    { "id": "1008000821", "name": "남위례", "timeToNext": 60 },   # 초 단위
    { "id": "1008000822", "name": "산성", "timeToNext": 60 },   # 초 단위
    { "id": "1008000823", "name": "남한산성입구(성남법원,검찰청)", "timeToNext": 60 },   # 초 단위
    { "id": "1008000824", "name": "단대오거리", "timeToNext": 60 },   # 초 단위
    { "id": "1008000825", "name": "신흥", "timeToNext": 60 },   # 초 단위
    { "id": "1008000826", "name": "수진", "timeToNext": 60 },   # 초 단위
    { "id": "1008000827", "name": "모란", "timeToNext": 60 },   # 초 단위
]

# 각 태그에 대한 메시지 데이터 구성
tag_messages = [
    # {"tag_key": "user_type", "tag_value": "premium", "message": "프리미엄 사용자에게 메시지"},
    # {"tag_key": "user_type", "tag_value": "basic", "message": "기본 사용자에게 메시지"},
    # 100개 이상의 태그와 메시지를 여기에 추가하세요.
]

# 상행과 하행을 구분할 리스트 초기화
# filtered_list = []
# uphill_trains = []
# downhill_trains = []
# up_push_msg = None
# down_push_msg = None


# 특정 열차의 예상 도착 시간을 계산
def calculate_time_to_arrival(station_list, current_station_name, train_station_name,updnLine):
    
    if(updnLine == "상행"):
        stations = list(reversed(station_list))
        t_num = 0
    else:
        stations = station_list
        t_num = 1
        
    # print(f"{updnLine} {current_station_name} {t_num} {stations}")
        
    current_index = next((i for i, s in enumerate(stations) if s["name"] == current_station_name), None)
    train_index = next((i for i, s in enumerate(stations) if s["name"] == train_station_name), None)
    
    if current_index is not None and train_index is not None and train_index < current_index:
        time_to_arrival = sum(station["timeToNext"] for station in stations[train_index + t_num:current_index+ t_num])
        return time_to_arrival
    return 0

def time_ago(date_time_str):
    recptn_dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    difference = now - recptn_dt

    # 경과된 시간 계산
    seconds = int(difference.total_seconds())
    minutes, seconds = divmod(seconds, 60)
    
    if minutes > 0:
        return f"{minutes}분 {seconds}초 전"
    else:
        return f"{seconds}초 전"


# def time_ago(date_time_str):
#     # 문자열을 datetime 객체로 변환
#     recptn_dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
#     now = datetime.now()
    
#     # 시간 차이 계산
#     diff = now - recptn_dt

#     # 시간에 따라 메시지 생성
#     if diff < timedelta(minutes=1):
#         return f"{diff.seconds}초 전"
#     elif diff < timedelta(hours=1):
#         minutes = diff.seconds // 60
#         return f"{minutes}분 전"
#     # elif diff < timedelta(days=1):
#     #     hours = diff.seconds // 3600
#     #     return f"{hours}시간 전"
#     # else:
#     #     days = diff.days
#     #     return f"{days}일 전"

def make_msgs_with_trains(trains,updnLine):
    global tag_messages
    push_msg = None
    push_title = None
    train_updn = None

    for item in trains:
        ordkey = item['ordkey']
        trainLineNm = item['trainLineNm']
        statnId = item['statnId']
        current_station_name = item['statnNm']
        btrainNo = item['btrainNo']
        arvlMsg2 = item['arvlMsg2']
        train_station_name = item['arvlMsg3']
        recptnDt = item['recptnDt']
        btrainSttus = item['btrainSttus']#일반, 급행
        lstcarAt = item['lstcarAt']#막차 여부: 0      
        train_updn = item['updnLine']

        if(arvlMsg2[0:2] == "전역"):
            arvlMsg2 = f"{arvlMsg2}({train_station_name})"

        time_to_arrival = calculate_time_to_arrival(station_times, current_station_name, train_station_name,train_updn)
        msg_temp = f"{train_updn}({btrainNo}) {arvlMsg2} : {time_to_arrival}초 후 도착"
        # print(msg_temp)
        if(push_msg):
            push_msg = f"{push_msg}\n{msg_temp}"
        else:
            # push_msg = f"{ordkey} {btrainNo}({arvlMsg2}/{arvlMsg3}) {recptnDt}"
            push_msg = msg_temp


    push_title = f"{current_station_name}역({trainLineNm}) {time_ago(recptnDt)}"
    
    updn = "0" if train_updn == "상행" else "1"
    tag_key = f"s-{statnId}-{updn}"
    tag_val = "true"
    print(push_msg,push_title,tag_key,tag_val)
    tag_messages.append({"tag_key": tag_key, "tag_value": tag_val, "message": push_msg, "title": push_title})


def fetch_arrival_data():
    global arrivalList
    global pushMsg
    global stationId
    ArrivalApiUrl = f"{REALMETRO_BASE_URL}/api/subway/{SEOUL_API_KEY}/json/realtimeStationArrival/0/10/{stationName}"
    # ArrivalApiUrl = f"{REALMETRO_BASE_URL}/api/subway/{SEOUL_API_KEY}/json/realtimeStationArrival/ALL"
    print(ArrivalApiUrl)
    try:
        response = requests.get(ArrivalApiUrl)  # 외부 API URL을 변경하세요
        print(response)
        if response.status_code == 200:
            data = response.json()

            filtered_list = []
            uphill_trains = []
            downhill_trains = []

            # stationIds에 있는 statnId와 일치하는 데이터만 필터링
            filtered_list = [item for item in data["realtimeArrivalList"] if item["statnId"] in stationIds]
            print(f"{stationIds} filtered_list size:{len(filtered_list)} {filtered_list}")

            # 역별로 구분하여 상행과 하행으로 나누기
            grouped_by_station = {}
            for item in filtered_list:
                statn_id = item["statnId"]
                if statn_id not in grouped_by_station:
                    grouped_by_station[statn_id] = {"상행": [], "하행": []}
                
                # 상행과 하행 구분하여 저장
                direction = item["updnLine"]
                if direction == "상행":
                    grouped_by_station[statn_id]["상행"].append(item)
                elif direction == "하행":
                    grouped_by_station[statn_id]["하행"].append(item)

            # 결과 출력
            for station, directions in grouped_by_station.items():
                print(f"역 ID: {station}")
                for direction, trains in directions.items():
                    print(f"  {direction}:")
                    make_msgs_with_trains(trains, direction)
                    # for train in trains:
                    #     print(f"    열차번호: {train['btrainNo']}, 도착정보: {train['arvlMsg2']}")

            # 상행과 하행 리스트에 데이터 추가
            # for train in filtered_list:
            #     if train["updnLine"] == "상행":
            #         uphill_trains.append(train)
            #     elif train["updnLine"] == "하행":
            #         downhill_trains.append(train)

            # print(f"API 호출 성공 ! uphill_trains:{uphill_trains} downhill_trains:{downhill_trains}")


            # send_push_for_trains(uphill_trains, "0")
            # send_push_for_trains(downhill_trains, "1")

            # print(f"API 호출 성공 ! data:{data}")
            # if len(arrivalList) == 0:
            #     arrivalList = data['realtimeArrivalList']
            #     print(f"init realtimeArrivalList: {arrivalList}")
            #     for item in arrivalList:
            #         ordkey = item['ordkey']
            #         trainLineNm = item['trainLineNm']
            #         btrainNo = item['btrainNo']
            #         arvlMsg2 = item['arvlMsg2']
            #         arvlMsg3 = item['arvlMsg3']
            #         recptnDt = item['recptnDt']


            #         pushMsg = f"{pushMsg}\n{ordkey} {btrainNo}({arvlMsg2}/{arvlMsg3}) {recptnDt}"

            # else:
            #     for item in data['realtimeArrivalList']:
            #         for arrival in arrivalList:
            #             if item['btrainNo'] == arrival['btrainNo']:
            #                 if item['recptnDt'] != arrival['recptnDt']:

                                
            #                     ordkey = item['ordkey']
            #                     trainLineNm = item['trainLineNm']
            #                     btrainNo = item['btrainNo']
            #                     arvlMsg2 = item['arvlMsg2']
            #                     arvlMsg3 = item['arvlMsg3']
            #                     recptnDt = item['recptnDt']

            #                     pushMsg = f"{pushMsg}\n{ordkey} {btrainNo}({arvlMsg2}/{arvlMsg3}) {recptnDt}"

            #                     arrival['recptnDt'] = item['recptnDt']
            #                 else:
            #                     print(f"{item['btrainNo']}:{arrival['recptnDt']} == {item['recptnDt']}")

            
            # pushTitle = f"{stationName}역({trainLineNm}) 도착 정보 {recptnDt}"
            # print(pushMsg,pushTitle)
            # send_push_message(pushMsg,pushTitle, "stationId", stationId)
    

            return "api return data"  # JSON 형식의 데이터를 반환
        else:
            print(f"API 호출 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"오류 발생: {e}")
        return None



# OneSignal을 통해 태그로 푸시 메시지를 보내는 함수
def send_push_message(message, heading, tag_key, tag_value):

    if message == "" or message == None:
        print(f"메시지가 없습니다. message:{message} heading:{heading}")
        return

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {ONESIGNAL_API_KEY}"
    }
    
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "filters": [
            {"field": "tag", "key": tag_key, "relation": "=", "value": tag_value}
        ],
        "contents": {"en": message},
        "headings": {"en": heading},
        # "included_segments": ["Total Subscriptions"],
                # Notification ID 설정 (external_id)
        "collapse_id": "update_notification_12345",
        "android_channel_id": "5dc736b4-9836-4915-a24a-be85964c337d"
        # Priority 설정
        # "android_priority": 10,  # Android: 10 = 높은 우선순위
        # "ios_priority": 10,      # iOS: 10 = 높은 우선순위 (즉시 표시)

        # 무음 설정
        # "ios_sound": "nil"        # iOS 무음 설정


    }

    # Add notification update/grouping parameters
       # Add notification update ID if provided
    # if existing_notification_id:
    #     payload["existing_android_notification_id"] = existing_notification_id
    #     payload["existing_ios_notification_id"] = existing_notification_id
   
    payload["android_group"] = "train_updates"
    # payload["collapse_id"] = collapse_id

    print(payload)

    response = requests.post(ONESIGNAL_URL, headers=headers, data=json.dumps(payload))
    
    if response.status_code == 200:
        print(f"푸시 메시지 전송 :{message}")
        print(f"푸시 메시지 전송 성공: {response.json()}")
        return response.json()
    else:
        print(f"푸시 메시지 전송 실패: {response.status_code}")



# 비동기 푸시 메시지 전송 함수
async def send_push_message_async(session, tag_key, tag_value, message, heading):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {ONESIGNAL_API_KEY}"
    }
    
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "filters": [
            {"field": "tag", "key": tag_key, "relation": "=", "value": tag_value}
        ],
        "contents": {"en": message},
        "headings": {"en": heading},
        "collapse_id": f"{tag_key}_{tag_value}",
        "android_channel_id": "5dc736b4-9836-4915-a24a-be85964c337d",
        "android_group" : "train_updates",
        "android_priority": 10,
        "ios_priority": 10,
        "android_sound": None,
        "ios_sound": None
    }
    
    async with session.post(ONESIGNAL_URL, headers=headers, json=payload) as response:
        if response.status == 200:
            print(f"{tag_key} {tag_value} 태그에 메시지 전송 성공!")
        else:
            print(f"{tag_key} {tag_value} 태그에 메시지 전송 실패: {response.status}")


# 모든 태그 메시지를 비동기로 전송하는 함수
async def send_bulk_messages():
    print(f"send_bulk_messages {len(tag_messages)}")
    async with aiohttp.ClientSession() as session:
        tasks = [
            send_push_message_async(session, item['tag_key'], item['tag_value'], item['message'],item['title'])
            for item in tag_messages
        ]
        
        # 모든 태그 메시지 전송을 병렬로 실행
        await asyncio.gather(*tasks)


# 30초 간격으로 API 데이터를 가져와서 푸시 메시지를 전송하는 메인 함수
cnt = 0

def main():
    global cnt
    global tag_messages

    # while True:
    while cnt < 100:
        tag_messages = []
        data = fetch_arrival_data()
        if data:
            print(data)
            asyncio.run(send_bulk_messages())

        # response = send_push_message(pushMsgBody,pushMsgTitle, "stationId", stationId)
        # existing_notification_id = response.get('id')
        # android_notification_id = response['android_notification_id']
        # ios_notification_id = response['ios_notification_id']
        # 30초 대기
        time.sleep(30)
        cnt = cnt + 1
        print(f"cnt:{cnt}")

    print("main end!")

if __name__ == "__main__":
    main()
