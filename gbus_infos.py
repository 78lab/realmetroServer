import aiohttp
import httpx
import requests
# import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import asyncio
from pymongo import UpdateOne
# import xml.etree.ElementTree as ET

from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List

from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 1. Pydantic 모델 정의 (데이터 검증 및 일관성 유지)
class BusRoute(BaseModel):
    routeId: str  # 문자열
    adminName: str
    endStationId: str
    endStationName: str
    regionName: str
    routeName: str
    routeTypeCd: str
    startStationId: str
    startStationName: str
    # turnSeq: int = Field(default=0)  # 정수 변환 (기본값 0)
    companyId: str
    companyName: str
    companyTel: Optional[str] = Field(default="")  # 전화번호 기본값 ""
    upFirstTime: str
    upLastTime: str
    downFirstTime: str
    downLastTime: str
    # peekAlloc: int = Field(default=0)  # 정수 변환 (기본값 0)

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

GBUS_ROUTE_INFOS_URL = "http://openapi.gbis.go.kr/ws/download?route20250211V2.txt"


def upsert_route_infos():
    # async with aiohttp.ClientSession() as session:
    # async with httpx.AsyncClient() as client:
    response = requests.get(GBUS_ROUTE_INFOS_URL)
    # response = await client.get(GBUS_ROUTE_INFOS_URL, params={})
    # print(response)
    if response.status_code != 200:
        print(f"Error fetching data upsert_route_infos {response.status_code}")
        return []
    else:
        # 2. 데이터 파싱
        # print("text:",response.text)
        raw_data = response.text.strip()  # 응답에서 불필요한 공백 제거
        rows = raw_data.split("^")  # 행 구분
        headers = rows[0].split("|")  # 첫 번째 행을 헤더로 사용

        data_list: List[BusRoute] = []

        for row in rows[1:]:
            if not row:
                continue  # 빈 행 건너뜀
            values = row.split("|")
            data_dict = dict(zip(headers, values))  # 헤더와 값 매핑
            
            try:
                # Pydantic 모델을 사용하여 검증 및 변환
                validated_data = BusRoute(**data_dict)
                data_list.append(validated_data.dict())  # MongoDB에 저장할 딕셔너리 변환
            except ValidationError as e:
                print(f"데이터 검증 실패: {e}")
                print(f"실패한 데이터: {data_dict}")

        # data_list = [dict(zip(headers, row.split("|"))) for row in rows[1:] if row]  # 각 행을 딕셔너리로 변환
        # print("data_list:",data_list)
        # 3. 데이터베이스에 저장
        # for data in data_list:
        #     # 데이터베이스에 저장하는 로직
        #     print(data)

        # 4. Upsert (routeId 기준으로 삽입 또는 업데이트)
        operations = [
            UpdateOne(
                {"routeId": data["routeId"]},  # 조건 (routeId가 같으면 업데이트)
                {"$set": data},  # 업데이트 내용 (모든 필드 갱신)
                upsert=True  # 없으면 삽입, 있으면 업데이트
            )
            for data in data_list
        ]

        if operations:
            result = collection.bulk_write(operations)
            print(f"업서트 완료!!: 삽입 {result.upserted_count}개, 업데이트 {result.modified_count}개")

async def main():
    print(f"upsert_route_infos start !!")
    upsert_route_infos()


# 이벤트 루프 실행
asyncio.run(main())