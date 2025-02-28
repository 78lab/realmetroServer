import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi

from pymongo import UpdateOne, UpdateMany, DeleteMany
# import aiohttp
# import httpx
import requests
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

PUB_DATA_API_KEY = os.getenv("PUB_DATA_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")
ONESIGNAL_APP_ID = os.getenv("ONESIGNAL_APP_ID") # '6799258c-2608-40ae-ae58-9ab570921e4b'
ONESIGNAL_API_KEY = os.getenv("ONESIGNAL_API_KEY") # 'MDc5YzU2ZmQtODY3Zi00YjMwLThmODgtNDg3OGQ1NTllN2Rj'
SEOUL_API_KEY = os.getenv("SEOUL_API_KEY") # "53797461466e65723730665567764a"  #'486a4d6c796e6572383276786c626a'

PUB_DATA_BASE_URL = 'http://apis.data.go.kr'
ONESIGNAL_URL = 'https://onesignal.com/api/v1/notifications'
REALMETRO_BASE_URL = 'http://swopenapi.seoul.go.kr'

# TRAIN_OFFSET_ARRIVAL = 25
# TRAIN_OFFSET_WILL_ARRIVAL = 60
# Set the Stable API version when creating a new client
client = AsyncIOMotorClient(MONGODB_URI, server_api=ServerApi('1'))

db = client['test']  # 데이터베이스 이름
train_collection = db['trains']  # 컬렉션 이름
timetable_collection = db['timetables']  # 컬렉션 이름

upDown = "1"  # 상행
realtimePositions = []
arrivalList = []

# async def ping_server():
#   # Replace the placeholder with your Atlas connection string

#   # Set the Stable API version when creating a new client
#   client = AsyncIOMotorClient(uri, server_api=ServerApi('1'))

#   # Send a ping to confirm a successful connection
#   try:
#       await client.admin.command('ping')
#       print("Pinged your deployment. You successfully connected to MongoDB!")
#   except Exception as e:
#       print(e)



# 오늘 날짜 가져오기
today = datetime.now()
today_formatted_date = today.strftime('%Y%m%d')
print(f"today_formatted_date:{today_formatted_date}")

async def get_rest_days():
    # 공휴일 API URL
    HOLIDAY_API_URL = f"{PUB_DATA_BASE_URL}/getRestDeInfo?serviceKey={PUB_DATA_API_KEY}&solYear={today.year}&solMonth={today.month}"
    print(f"HOLIDAY_API_URL:{HOLIDAY_API_URL}")
    response = requests.get(HOLIDAY_API_URL)
    if response.status_code == 200:
        data = response.json()
        rest_days = [item['locdate'] for item in data['response']['body']['items']['item']]
        return rest_days
    else:
        return []

# 외부 API로부터 데이터를 가져오는 함수
async def fetch_realtime_train_data(subwayName, weekTag):
    global realtimePositions
    REALMETRO_API_URL = f"{REALMETRO_BASE_URL}/api/subway/{SEOUL_API_KEY}/json/realtimePosition/0/200/{subwayName}"
    print(f"REALMETRO_API_URL:{REALMETRO_API_URL} weekTag:{weekTag}")
    try:
        response = requests.get(REALMETRO_API_URL)  # 외부 API URL을 변경하세요
        print(response)
        if response.status_code == 200:
            data = response.json()
            print(f"API 호출 성공 ! data len:{len(data['realtimePositionList'])}")
            # 중복 검사 및 데이터 삽입 또는 업데이트
            operations = []
            timetable_opertions = []

            cnt = 0

            for item in data['realtimePositionList']:
                cnt += 1
                # print(f"item:{item}")

                trainNo = item['trainNo']
                # statnTnm = item['statnTnm']
                statnId = item['statnId']
                #1-9호선 뒤 3자리 코드
                frCode = statnId[7:10]
                statnNm = item['statnNm']
                recptnDt = item['recptnDt']
                # updnLine = item['updnLine']
                trainSttus = item['trainSttus']
                # directAt = item['directAt']
                # lstcarAt = item['lstcarAt']
                

                train_delay,tt_train_no = await cal_train_delay_async(frCode,trainNo, weekTag,recptnDt,trainSttus)
                print(f"{cnt}: train_delay:{train_delay} tt_train_no:{tt_train_no} statnId:{statnId} FR_CODE:{frCode}  trainSttus:{trainSttus}")

                if train_delay:
                    #trains updates
                    filter_key = {
                        "TRAIN_NO": tt_train_no
                    }

                    item['TRAIN_NO'] = tt_train_no
                    item['delay'] = train_delay
                    
                    update_data = {"$set": item}
                    operations.append(UpdateOne(filter_key, update_data, upsert=True))

                    #timetable updates    
                    tt_filter_key = {
                        "TRAIN_NO": tt_train_no,
                        "FR_CODE": frCode,
                        "WEEK_TAG": weekTag
                    }

                    tt_update_data = {"$set": {'statnId':statnId, 'statnNm':statnNm, 'recptnDt':recptnDt,'trainSttus':trainSttus,'delay':train_delay}}
                    timetable_opertions.append(UpdateOne(tt_filter_key, tt_update_data))

                else:
                    print(f"train_delay is none:{train_delay}")

                
            # MongoDB에 대량 요청 실행
            if len(operations) > 0:
                operations.append(DeleteMany({"$expr": { "$eq": ["$statnId", "$statnTid"] }}))
                # result = await train_collection.delete_many({ "lastRecptnDt": { "$lt": today_formatted_date }})
                # result = await train_collection.delete_many({"$expr": { "$eq": ["$statnId", "$statnTid"] }})
                # print(f"today:{today_formatted_date} train:{trainNo} deleted: {result.deleted_count}")
                result = await train_collection.bulk_write(operations)
                # result = await timetable_collection.bulk_write(operations)
                print(f"weekTag:{weekTag} trains I: {result.upserted_count}, U: {result.modified_count} D: {result.deleted_count}")

            if len(timetable_opertions) > 0:

                result = await timetable_collection.bulk_write(timetable_opertions)
                print(f"weekTag:{weekTag} timetable  U: {result.modified_count}")

            # if len(realtimePositions) == 0:
            #     realtimePositions = data['realtimePositionList']
            #     print(f"init realtimePositions: {realtimePositions}")
            # else:
            #     for item in data['realtimePositionList']:
            #         for realtimePosition in realtimePositions:
            #             if item['trainNo'] == realtimePosition['trainNo']:
            #                 if item['recptnDt'] != realtimePosition['recptnDt']:

                                

            #                     trainNo = item['trainNo']
            #                     statnTnm = item['statnTnm']
            #                     statnId = item['statnId']
            #                     trainSttus = item['trainSttus']
            #                     statnNm = item['statnNm']

            #                     message = f"[{statnTnm}행{trainNo}({statnNm}:{trainSttus}) {realtimePosition['recptnDt']} -> {item['recptnDt']}"


            #                     print(message)
            #                     send_push_message(message,"", "statnId", statnId)

            #                     realtimePosition['recptnDt'] = item['recptnDt']
            #                 else:
            #                     print(f"{item['trainNo']}:{realtimePosition['recptnDt']} == {item['recptnDt']}")
                    

            return "api return data"  # JSON 형식의 데이터를 반환
        else:
            print(f"API 호출 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"오류 발생: {e}")
        return None


async def cal_train_delay_async(frCode, trainNo, weekTag, recptnDt, train_stat):
    print(f"\n\n\ncal_delay_async...frCode:{frCode} trainNo:{trainNo} weekTag:{weekTag} recptnDt:{recptnDt} train_stat: {train_stat}") 

    train_delay_arrivetime = None
    train_delay_lefttime = None

    document = await find_timetable_async(frCode, trainNo,weekTag)

    if document:
        print(f"document:{document['TRAIN_NO']}")
        # print(f"ARRIVETIME: {document['ARRIVETIME']}, LEFTTIME: {document['LEFTTIME']}")
        # if document['ARRIVETIME'] == "00:00:00" or document['LEFTTIME'] == "00:00:00":
        #     return None


        current_time = datetime.now().replace(microsecond=0)
        today = current_time.date()  # 오늘 날짜
        print(f"현재 시간: {current_time} trainNo: {trainNo} train_stat: {train_stat} A:{document['ARRIVETIME']} L:{document['LEFTTIME']}")

        recptntime = datetime.strptime(recptnDt, "%Y-%m-%d %H:%M:%S")


        if recptntime > current_time:
            print(f"!!!! recptntime > current_time: {recptntime} > {current_time}")
            return None,None  # 현재 시간보다 미래인 경우 None 반환 혹은 다른 처리 수행

        # 현재 시간과 비교하여 가장 가까운 시간을 찾아 차이를 계산
        # if document['ARRIVETIME'] != "00:00:00":
        #     arrivetime = datetime.combine(today, datetime.strptime(document["ARRIVETIME"], "%H:%M:%S").time())
        #     arrivetime_diff = (arrivetime - current_time).total_seconds()
        #     train_delay_arrivetime = (recptntime - arrivetime).total_seconds()
        #     print(f"arrivetime_diff:{arrivetime_diff} train_delay_arrivetime: {train_delay_arrivetime}")

        if document['ARRIVETIME'] != "00:00:00":
            arrivetime = datetime.combine(today, datetime.strptime(document["ARRIVETIME"], "%H:%M:%S").time())
            arrivetime_diff = (arrivetime - current_time).total_seconds()
            train_delay_arrivetime = (recptntime - arrivetime).total_seconds()
            # print(f"arrivetime_diff:{arrivetime_diff} train_delay_arrivetime: {train_delay_arrivetime}")

        if document['LEFTTIME'] != "00:00:00":
            lefttime = datetime.combine(today, datetime.strptime(document["LEFTTIME"], "%H:%M:%S").time())
            lefttime_diff = (lefttime - current_time).total_seconds()
            train_delay_lefttime = (recptntime - lefttime).total_seconds()
            # print(f"lefttime_diff:{lefttime_diff} train_delay_lefttime: {train_delay_lefttime}")


        train_delay = 0
        delay_offset = 0

        if train_stat == "0" and train_delay_arrivetime:
            delay_offset = 50
            train_delay = train_delay_arrivetime + delay_offset
            print(f"train_stat:0 {train_delay_arrivetime} + {delay_offset} = {train_delay}")
        elif train_stat == "1" and train_delay_arrivetime:
            delay_offset = 25
            train_delay = train_delay_arrivetime + delay_offset
            print(f"train_stat:1 {train_delay_arrivetime} + {delay_offset} = {train_delay}")
        elif train_stat == "2" and train_delay_lefttime:
            train_delay = train_delay_lefttime
            print(f"train_stat:2 train_delay_lefttime = {train_delay}")
        else:
            print(f"!! train_stat:{train_stat} ARRIVETIME:{document['ARRIVETIME']} LEFTTIME:{document['LEFTTIME']}")
 

        # if arrivetime_diff > 0:
        #     a_minutes, a_seconds = divmod(int(arrivetime_diff), 60)
        #     print(f"{inout_tag}:{fr_code_value} {train_no}열차 {a_minutes}분 {a_seconds}초 후 도착")
        # else:
        #     l_minutes, l_seconds = divmod(int(lefttime_diff), 60)
        #     print(f"{inout_tag}:{fr_code_value} {train_no}열차 {l_seconds}초 후 출발")
    
        return train_delay, document['TRAIN_NO']
    else:
        print(f"NO document!! cal_delay_async...frCode:{frCode} trainNo:{trainNo}")
        return None,None



async def find_timetable_async(frCode, trainNo, weekTag):
    # current_time = datetime.now().strftime("%H:%M:%S") {"$regex": "^3266"}
    # query = { "FR_CODE": frCode, "TRAIN_NO": trainNo, "WEEK_TAG": weekTag }
    query = { "FR_CODE": frCode, "TRAIN_NO": {"$regex": trainNo}, "WEEK_TAG": weekTag }
    print(query)
    result = await timetable_collection.find_one(query)
    return result
# 특정 FR_CODE 값을 가진 데이터를 찾는 비동기 함수

# 특정 조건을 가진 데이터를 찾는 비동기 함수
async def find_arrivals_by_updn_async(updn):
    current_time = datetime.now().strftime("%H:%M:%S")
    query = {
        "LEFTTIME": {"$gt": current_time},
        "INOUT_TAG": updn
    }
    # query = {"INOUT_TAG": updn}
    print(query)
    # 문서 조회
    documents = []
    async for document in collection.find(query):
        documents.append(document)
    
    return documents

async def find_next_arrival_async(fr_code, updn):
    current_time = datetime.now().strftime("%H:%M:%S")
    query = {"LEFTTIME": {"$gt": current_time}, "FR_CODE": fr_code, "INOUT_TAG": updn}
    # print(query)
    result = await collection.find_one(query)
    return result

async def find_by_fr_code_async(fr_code):
    query = {"FR_CODE": fr_code}
    result = await collection.find_one(query)
    return result

# 예제 비동기 함수 실행
async def cal_time_diff_async(fr_code_value, updn):
    # print(f"cal_time_diff_async...fr_code_value:{fr_code_value}")
    # fr_code_value = "818"
    # document = await find_by_fr_code_async(fr_code_value)
    document = await find_next_arrival_async(fr_code_value, updn)
    # print(document)

    if document:
        current_time = datetime.now().replace(microsecond=0)
        today = current_time.date()  # 오늘 날짜
        # ARRIVETIME과 LEFTTIME을 datetime 형식으로 변환
        # ARRIVETIME을 datetime 형식으로 변환하고 오늘 날짜로 설정
        train_no = document["TRAIN_NO"]
        inout_tag = document["INOUT_TAG"]
        arrivetime = datetime.combine(today, datetime.strptime(document["ARRIVETIME"], "%H:%M:%S").time())
        lefttime = datetime.combine(today, datetime.strptime(document["LEFTTIME"], "%H:%M:%S").time())

        # print(f"ARRIVETIME lefttime: {arrivetime} {lefttime}")
        # 시간차 계산
       
        print(f"현재 시간: {current_time} 열차번호: {train_no} updn:{inout_tag}")
        arrivetime_diff = (arrivetime - current_time).total_seconds()
        lefttime_diff = (lefttime - current_time).total_seconds()
        
        # print(f"ARRIVETIME과 현재 시간의 차이(초): {arrivetime_diff}")
        # print(f"LEFTTIME과 현재 시간의 차이(초): {lefttime_diff}")

        if arrivetime_diff > 0:
            a_minutes, a_seconds = divmod(int(arrivetime_diff), 60)
            print(f"{inout_tag}:{fr_code_value} {train_no}열차 {a_minutes}분 {a_seconds}초 후 도착")
        else:
            l_minutes, l_seconds = divmod(int(lefttime_diff), 60)
            print(f"{inout_tag}:{fr_code_value} {train_no}열차 {l_seconds}초 후 출발")
        
        

        # return arrivetime_diff, lefttime_diff
    else:
        return None, None

# fr_code_list = ['804','805','806','807','808','809','810','811','812','813','814','815','816','817','818','819','820','821','822','823','824','825','826','827']
# fr_code_list = ['814','815','816','817','818','819','820','821','822','823','824','825','826','827']

# 예제 사용
async def main():
    print("Starting async main...")
    # updn = "2"


    result = await train_collection.delete_many({})
    print(f"clear train_collection deleted: {result.deleted_count}")


    cnt = 0

    weekTag = "1"
    current_time = datetime.now()   
    weekday = current_time.weekday()
   
    restdays = await get_rest_days()
    print(f"restdays:{restdays} today_formatted_date:{today_formatted_date}")
    if today_formatted_date in restdays or weekday == 6:
        weekTag = "3"
    elif weekday == 5:
        weekTag = "2"
    else:
        weekTag = "1"

     # 요일 확인 (0:월요일 ~ 6:일요일)
    print(f"weekTag: {weekTag}")

    # exit()

    while True:
    # while cnt < 2400: #10hours
        # 현재 시간 가져오기
        # doc = await find_timetable_async("824", "8162")
        # print(doc['ARRIVETIME'])
        # print(doc['LEFTTIME'])
        # await cal_train_delay_async("820", "8115","2024-11-21 11:48:37","2")
        
        await fetch_realtime_train_data("3호선",weekTag)
        await fetch_realtime_train_data("4호선",weekTag)
        await fetch_realtime_train_data("7호선",weekTag)
        await fetch_realtime_train_data("8호선",weekTag)
        cnt += 1
        print(f"cnt:{cnt}")
        # for fr_code_value in fr_code_list:
        #     await cal_time_diff_async(fr_code_value, updn)

        # docs = await find_arrivals_by_updn_async("1")
        # for doc in docs:
        #     print(doc)ß
        cur_time = datetime.now()
        print(f"cur_time:{cur_time.hour}:{cur_time.minute} ...")
        if cur_time.hour == 2: #and cur_time.minute == 13
            print(f"cur_time: {cur_time.hour}:{cur_time.minute} exit.")
            break

        await asyncio.sleep(5)  # 5초 대기


asyncio.run(main())
print("main end.")