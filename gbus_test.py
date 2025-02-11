import aiohttp
import httpx
# import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import asyncio
from pymongo import UpdateOne
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

ONESIGNAL_APP_ID = os.getenv("ONESIGNAL_APP_ID") # '6799258c-2608-40ae-ae58-9ab570921e4b'
ONESIGNAL_API_KEY = os.getenv("ONESIGNAL_API_KEY") # 'MDc5YzU2ZmQtODY3Zi00YjMwLThmODgtNDg3OGQ1NTllN2Rj'
ONESIGNAL_URL = 'https://onesignal.com/api/v1/notifications'

# 각 태그에 대한 메시지 데이터 구성
tag_messages = [
    # {"tag_key": "user_type", "tag_value": "premium", "message": "프리미엄 사용자에게 메시지"},
    # {"tag_key": "user_type", "tag_value": "basic", "message": "기본 사용자에게 메시지"},
    # 100개 이상의 태그와 메시지를 여기에 추가하세요.
]


# 환경 변수에서 API_KEY 및 DB_URI 불러오기
PUB_DATA_API_KEY = os.getenv("PUB_DATA_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")

client = AsyncIOMotorClient(MONGODB_URI, server_api=ServerApi('1'))

# client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017/')
db = client['test']  # 데이터베이스 이름
collection = db['busrouteinfos']  # 컬렉션 이름
BUS_BASE_URL = "https://apis.data.go.kr/6410000"
# BUS_ARRIVAL_URL = BUS_BASE_URL + "/busarrivalservice/getBusArrivalList?serviceKey={}&stationId={}"
# BUS_ROUTE_INFO_URL = BUS_BASE_URL+ "/busrouteservice/getBusRouteInfoItem?serviceKey={}&routeId={}"
BUS_ARRIVAL_URL = BUS_BASE_URL + "/busarrivalservice/v2/getBusArrivalListv2?serviceKey={}&stationId={}&format=json"
BUS_ROUTE_INFO_URL = BUS_BASE_URL+ "/busrouteservice/v2/getBusRouteInfoItemv2?serviceKey={}&routeId={}&format=json"


# def make_msgs_with_buses(buses):
#     global tag_messages
#     push_msg = None
#     push_title = None

#     for item in buses:
#         ordkey = item['ordkey']
#         trainLineNm = item['trainLineNm']
#         statnId = item['statnId']
#         current_station_name = item['statnNm']
#         btrainNo = item['btrainNo']
#         arvlMsg2 = item['arvlMsg2']
#         train_station_name = item['arvlMsg3']
#         recptnDt = item['recptnDt']
#         btrainSttus = item['btrainSttus']#일반, 급행
#         lstcarAt = item['lstcarAt']#막차 여부: 0      
#         train_updn = item['updnLine']

#         if(arvlMsg2[0:2] == "전역"):
#             arvlMsg2 = f"{arvlMsg2}({train_station_name})"

#         time_to_arrival = calculate_time_to_arrival(station_times, current_station_name, train_station_name,train_updn)
#         msg_temp = f"{train_updn}({btrainNo}) {arvlMsg2} : {time_to_arrival}초 후 도착"
#         # print(msg_temp)
#         if(push_msg):
#             push_msg = f"{push_msg}\n{msg_temp}"
#         else:
#             # push_msg = f"{ordkey} {btrainNo}({arvlMsg2}/{arvlMsg3}) {recptnDt}"
#             push_msg = msg_temp


#     push_title = f"{current_station_name}역({trainLineNm}) {time_ago(recptnDt)}"
    
#     updn = "0" if train_updn == "상행" else "1"
#     tag_key = f"s-{statnId}-{updn}"
#     tag_val = "true"
#     print(push_msg,push_title,tag_key,tag_val)
#     tag_messages.append({"tag_key": tag_key, "tag_value": tag_val, "message": push_msg, "title": push_title})

# 특정 stationId에 대한 routeId 리스트 가져오기
async def fetch_bus_routes(stationId):
    # async with aiohttp.ClientSession() as session:
    async with httpx.AsyncClient() as client:
        url = BUS_ARRIVAL_URL.format(PUB_DATA_API_KEY, stationId)
        # async with session.get(url) as response:
            # response_text = await response.text()
        response = await client.get(url, params={})

        if response.status_code != 200:
            print(f"Error fetching data for stationId {stationId} {response.status_code}")
            return []
        else:
            data = response.json()
            # print(data)
            resultCode = data['response']['msgHeader']['resultCode']
            if resultCode != 0:
                print(f"Error fetching data for stationId {stationId}")
                return []
            
            print(data['response']['msgBody']['busArrivalList'])  
            return data['response']['msgBody']['busArrivalList']
        
            # XML 파싱
            # root = ET.fromstring(response.text)
            # resultCode = root.find(".//resultCode").text
            # if resultCode != "0":
            #     print(f"Error fetching data for stationId {stationId}")
            #     return []

            # route_data = []
            # for item in root.findall(".//busArrivalList"):
            #     # XML에서 필요한 데이터 추출
            #     document = {
            #         "stationId": stationId,
            #         "routeId": item.find("routeId").text,
            #         "flag": item.find("flag").text,
            #         "locationNo1": item.find("locationNo1").text,
            #         "locationNo2": item.find("locationNo2").text if item.find("locationNo2") is not None else None,
            #         "lowPlate1": item.find("lowPlate1").text,
            #         "lowPlate2": item.find("lowPlate2").text if item.find("lowPlate2") is not None else None,
            #         "plateNo1": item.find("plateNo1").text,
            #         "plateNo2": item.find("plateNo2").text if item.find("plateNo2") is not None else None,
            #         "predictTime1": item.find("predictTime1").text,
            #         "predictTime2": item.find("predictTime2").text if item.find("predictTime2") is not None else None,
            #         "remainSeatCnt1": item.find("remainSeatCnt1").text,
            #         "remainSeatCnt2": item.find("remainSeatCnt2").text if item.find("remainSeatCnt2") is not None else None,
            #         "staOrder": item.find("staOrder").text,
            #     }
            #     route_data.append(document)
                
            # return route_data

async def upsert_route_data(route_data):
    operations = []
    for item in route_data:
         routeId = item["routeId"]
         operations.append(
             UpdateOne(
                 {"routeId": routeId},
                 {"$set": item},
                 upsert=True
             )
         )

    if operations:
        print(f"upsert_route_data operations: {operations}")
        result = await collection.bulk_write(operations)
        print(f"upsert_route_data Inserted: {result.upserted_count}, Updated: {result.modified_count}")


# API에서 데이터를 가져와 MongoDB에 업서트하는 함수
async def fetch_and_upsert(routeIds):
    # async with aiohttp.ClientSession() as session:
    async with httpx.AsyncClient() as client:
        operations = []
        
        for routeId in routeIds:
            url = BUS_ROUTE_INFO_URL.format(PUB_DATA_API_KEY, routeId)
            # async with session.get(url) as response:
            #     response_text = await response.text()
            response = await client.get(url, params={})
            data = response.json()

            resultCode = data['response']['msgHeader']['resultCode']
            if resultCode != 0:
                print(f"Error fetching data for routeId {routeId}")
                return []
            
            print(routeId, data['response']['msgBody']['busRouteInfoItem']['routeName'])  
            busRouteInfoItem = data['response']['msgBody']['busRouteInfoItem']
            operations.append(
                UpdateOne(
                    {"routeId": routeId},
                    {"$set": busRouteInfoItem},
                    upsert=True
                )
            )

            # return data['response']['msgBody']['busRouteInfoItem']
            # if response.status_code != 200:
            #     print(f"Error fetching data for routeId {routeId} {response.status_code}")
            #     return []
            # else:
            #     print(f"Fetched data for routeId {routeId}: {response.text}")

            #     # return;
            #     # XML 파싱
            #     root = ET.fromstring(response.text)
            #     resultCode = root.find(".//resultCode").text
            #     if resultCode != "0":
            #         print(f"Error fetching data for routeId {routeId}")
            #         continue

            #     # XML에서 필요한 데이터 추출
            #     item = root.find(".//busRouteInfoItem")
            #     if item is not None:
            #         endMobileNo = item.find("endMobileNo")
            #         if endMobileNo is not None:
            #             endMobileNo = endMobileNo.text
            #         else:
            #             endMobileNo = ""

            #         startMobileNo = item.find("startMobileNo")
            #         if startMobileNo is not None:
            #             startMobileNo = startMobileNo.text
            #         else:
            #             startMobileNo = ""


            #         document = {
            #             "routeId": item.find("routeId").text,
            #             "routeName": item.find("routeName").text,
            #             "routeTypeCd": item.find("routeTypeCd").text,
            #             "routeTypeName": item.find("routeTypeName").text,
            #             "companyId": item.find("companyId").text,
            #             "companyName": item.find("companyName").text,
            #             "companyTel": item.find("companyTel").text,
            #             "districtCd": item.find("districtCd").text,
            #             "startMobileNo": startMobileNo,
            #             "startStationId": item.find("startStationId").text,
            #             "startStationName": item.find("startStationName").text,
            #             "endMobileNo": endMobileNo,
            #             "endStationId": item.find("endStationId").text,
            #             "endStationName": item.find("endStationName").text,
            #             "upFirstTime": item.find("upFirstTime").text,
            #             "upLastTime": item.find("upLastTime").text,
            #             "downFirstTime": item.find("downFirstTime").text,
            #             "downLastTime": item.find("downLastTime").text,
            #             "peekAlloc": item.find("peekAlloc").text,
            #             "nPeekAlloc": item.find("nPeekAlloc").text,
            #             "regionName": item.find("regionName").text,
            #             # 필요한 추가 필드를 추출할 수 있습니다.
            #         }

            #         # Upsert operation 준비
            #         operations.append(
            #             UpdateOne(
            #                 {"routeId": document["routeId"]},  # 필터 조건 (routeId 기준 중복 체크)
            #                 {"$set": document},                 # 중복된 경우 업데이트, 아니면 삽입
            #                 upsert=True
            #             )
            #         )

        # MongoDB에 bulk upsert 수행
        if operations:
            print(f"operations: {operations}")
            result = await collection.bulk_write(operations)
            print(f"Inserted: {result.upserted_count}, Updated: {result.modified_count}")

# 예제 사용
# async def main():
#     routeIds = ["222000200", "241347005"]  # 조회할 routeId 목록
#     await fetch_and_upsert(routeIds)

# MongoDB에 bulk upsert하는 함수
async def upsert_routes_for_station(stationId):
    # global tag_messages
    route_data = await fetch_bus_routes(stationId)
    
    if not route_data:
        print("No data found for stationId:", stationId)
        return
    
    routeIds = [route["routeId"] for route in route_data]
    print(f"routeIds: {routeIds}")

    # push_msg = "msg:"
    for route in route_data:
        routeId = route["routeId"]
        # 필터 조건 (stationId, routeId 기준 중복 체크)
        filter = { "routeId": routeId}
        print(f"filter:{filter}")
        result = await collection.find_one(filter)
        print(f"result:{result}")

        if result is None:
            print(f"None routeId : {route['routeId']}")
            await fetch_and_upsert([routeId])
            # await upsert_route_data(route_data)
        else:
            temp_str_1 = f"Route exists: {route['routeId']} {result['regionName']}|{result['routeName']} {result['routeTypeName']} | {result['startStationName']}>{result['endStationName']}"
            # temp_str_2 = f"Route {route['flag']} sta:{route['staOrder']} {route['predictTime1']}분/{route['locationNo1']}전/저상{route['lowPlate1']} {route['predictTime2']}분/{route['locationNo2']}전/저상{route['lowPlate2']}"
            print(temp_str_1)
            # print(temp_str_2)
            # push_msg = push_msg + temp_str_1 + "\n" + temp_str_2 + "\n"
    
    # tag_messages.append({"tag_key": "s-1008000818-0", "tag_value": "true", "message": push_msg, "heading": "GBUS"})
           


# 비동기 푸시 메시지 전송 함수
# async def send_push_message_async(session, tag_key, tag_value, message, heading):
#     headers = {
#         "Content-Type": "application/json; charset=utf-8",
#         "Authorization": f"Basic {ONESIGNAL_API_KEY}"
#     }
    
#     payload = {
#         "app_id": ONESIGNAL_APP_ID,
#         "filters": [
#             {"field": "tag", "key": tag_key, "relation": "=", "value": tag_value}
#         ],
#         "contents": {"en": message},
#         "headings": {"en": heading},
#         "collapse_id": f"{tag_key}_{tag_value}",
#         "android_channel_id": "cd188376-cfd1-4e84-ae89-0bf56353d1b3",
#         "android_group" : "bus_updates",
#         "android_priority": 10,
#         "ios_priority": 10,
#         # "android_sound": None,
#         # "ios_sound": None
#     }
#     print(f"payload: {payload}")
    
#     async with session.post(ONESIGNAL_URL, headers=headers, json=payload) as response:
#         if response.status == 200:
#             print(f"{tag_key} {tag_value} 태그에 메시지 전송 성공!")
#         else:
#             print(f"{tag_key} {tag_value} 태그에 메시지 전송 실패: {response.status}")

# 모든 태그 메시지를 비동기로 전송하는 함수
# async def send_bulk_messages():
#     global tag_messages
#     print(f"send_bulk_messages {len(tag_messages)} {tag_messages}")
#     async with aiohttp.ClientSession() as session:
#         tasks = [
#             send_push_message_async(session, item['tag_key'], item['tag_value'], item['message'],item['heading'])
#             for item in tag_messages
#         ]
        
#         # 모든 태그 메시지 전송을 병렬로 실행
#         await asyncio.gather(*tasks)
#         tag_messages = []

# stationList = ['222000182',
# '222000199',
# '222000200',
# '221000041',
# '241005890',
# '241347007',
# '241347009',
# '241347010',
# '241350003',
# '241347002']
# 예제 사용
async def main():

    # for stationId in stationList:
    #     await upsert_routes_for_station(stationId)
    stationId = "222001539"  # 조회할 stationId
    print(f"stationId: {stationId}")
    await upsert_routes_for_station(stationId)
    # resData = await fetch_bus_routes(stationId)
    # print(f"resData: {resData}")
    # cnt = 0
    # while cnt < 100:
    #     await upsert_routes_for_station(stationId)
    #     await send_bulk_messages()
    #     print(f"cnt: {cnt}")
    #     cnt += 1
    #     await asyncio.sleep(30)  # 30초 대기

# 이벤트 루프 실행
asyncio.run(main())