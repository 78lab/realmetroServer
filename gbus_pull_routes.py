# import aiohttp
import httpx
import ssl
import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import asyncio
from pymongo import UpdateOne
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import os

# Create a custom SSL context
ssl_context = ssl.create_default_context()
ssl_context.options |= ssl.OP_NO_SSLv2  # Disable SSLv2 (if not already disabled)
ssl_context.options |= ssl.OP_NO_SSLv3  # Disable SSLv3 as it's insecure
ssl_context.options |= ssl.OP_NO_COMPRESSION  # Disable compression to prevent potential vulnerabilities
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2  # Enforce at least TLS 1.2

# Optionally disable hostname checking if necessary (use with caution)
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API_KEY 및 DB_URI 불러오기
PUB_DATA_API_KEY = os.getenv("PUB_DATA_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")

client = AsyncIOMotorClient(MONGODB_URI, server_api=ServerApi('1'))

# client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017/')
db = client['test']  # 데이터베이스 이름
# collection = db['busarrivals']  # 컬렉션 이름
bus_route_collection = db['busrouteinfos']  # 컬렉션 이름
BUS_BASE_URL = "https://apis.data.go.kr/6410000"
BUS_ARRIVAL_URL = BUS_BASE_URL + "/busarrivalservice/getBusArrivalList?serviceKey={}&stationId={}"
BUS_ROUTE_INFO_URL = BUS_BASE_URL+ "/busrouteservice/getBusRouteInfoItem?serviceKey={}&routeId={}"

params = {}
# 특정 stationId에 대한 routeId 리스트 가져오기
async def fetch_bus_routes(stationId):
    # async with aiohttp.ClientSession() as session:
    async with httpx.AsyncClient() as client:
        try:
            url = BUS_ARRIVAL_URL.format(PUB_DATA_API_KEY, stationId)
            # async with session.get(url, ssl=ssl_context) as response:
            response = await client.get(url, params=params)
            print(response.status_code, response.text)
            # response_text = response.text()
            # print(response_text)

            # XML 파싱
            root = ET.fromstring(response.text)
            resultCode = root.find(".//resultCode").text
            if resultCode != "0":
                print(f"Error fetching data for stationId {stationId}")
                return []

            route_data = []
            for item in root.findall(".//busArrivalList"):
                # XML에서 필요한 데이터 추출
                document = {
                    "stationId": stationId,
                    "routeId": item.find("routeId").text,
                    "flag": item.find("flag").text,
                    "locationNo1": item.find("locationNo1").text,
                    "locationNo2": item.find("locationNo2").text if item.find("locationNo2") is not None else None,
                    "lowPlate1": item.find("lowPlate1").text,
                    "lowPlate2": item.find("lowPlate2").text if item.find("lowPlate2") is not None else None,
                    "plateNo1": item.find("plateNo1").text,
                    "plateNo2": item.find("plateNo2").text if item.find("plateNo2") is not None else None,
                    "predictTime1": item.find("predictTime1").text,
                    "predictTime2": item.find("predictTime2").text if item.find("predictTime2") is not None else None,
                    "remainSeatCnt1": item.find("remainSeatCnt1").text,
                    "remainSeatCnt2": item.find("remainSeatCnt2").text if item.find("remainSeatCnt2") is not None else None,
                    "staOrder": item.find("staOrder").text,
                }
                route_data.append(document)
                
            return route_data
        except Exception as e:
            print("Error fetching data for stationId", stationId, ":", e)
        # except aiohttp.ClientConnectorSSLError as e:
        #     print("SSL Error:", e)

# MongoDB에 bulk upsert하는 함수
async def upsert_routes(stationId):
    route_data = await fetch_bus_routes(stationId)
    
    if not route_data:
        print("No data found for stationId:", stationId)
        return
    
    # Bulk upsert 준비
    operations = [
        UpdateOne(
            {"routeId": route["routeId"], "stationId": route["stationId"]},  # 필터 조건 (stationId, routeId 기준 중복 체크)
            {"$set": route},  # 기존에 존재하는 경우 업데이트
            upsert=True  # 존재하지 않는 경우 삽입
        )
        for route in route_data
    ]

    # MongoDB에 bulk upsert 수행
    if operations:
        print(f"operations:{operations} Upserting {len(operations)} documents for stationId {stationId}")
        result = await bus_route_collection.bulk_write(operations)
        print(f"bus_route_collection US: {result.upserted_count} and U: {result.modified_count} for stationId: {stationId}")


stationList = ['222000182',
'222000199',
'222000200',
'221000041',
'241005890',
'241347007',
'241347009',
'241347010',
'241350003',
'241347002']

# 예제 사용
async def main():
    # stationId = "222001901"  # 조회할 stationId

    for stationId in stationList:
        await upsert_routes(stationId)

# 이벤트 루프 실행
asyncio.run(main())
print("gbus pull station info :Done")