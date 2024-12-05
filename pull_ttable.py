import aiohttp
import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import asyncio
from pymongo import UpdateOne
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
# Set the Stable API version when creating a new client
client = AsyncIOMotorClient(MONGODB_URI, server_api=ServerApi('1'))

db = client['test']  # 데이터베이스 이름
collection = db['timetables']  # 컬렉션 이름
metrostation_collection = db['metrostations']  # 컬렉션 이름

# 공공 API 요청 URL 설정
API_KEY = os.getenv("SEOUL_OPEN_API_KEY")#'7378766f536e657231313670784b5a66'  # API 키를 여기에 넣으세요
BASE_URL = 'http://openAPI.seoul.go.kr:8088/{}/json/SearchSTNTimeTableByFRCodeService/1/500/{}/{}/{}'



async def fetch_metrostation_data(subway_id):
    metrostations = []
    filter_key = {"subwayId": subway_id}
    async for metrostation in metrostation_collection.find(filter_key).sort("statnId", 1):
        metrostations.append({
            "subwayId": metrostation["subwayId"],
            "statnId": metrostation["statnId"],
            "statnNm": metrostation["statnNm"]
        })
    return metrostations

# API 호출 및 MongoDB 삽입 함수
async def fetch_and_insert(fr_code, week_tag, inout_tag, subway_id):

    tdata = await collection.find_one({"subwayId":subway_id, "FR_CODE": fr_code, "WEEK_TAG": week_tag, "INOUT_TAG": inout_tag})

    if tdata:
        print(f"tdata: {subway_id} fr_code:{fr_code} week_tag:{week_tag}  inout_tag:{inout_tag} ")
        return

    url = BASE_URL.format(API_KEY, fr_code, week_tag, inout_tag)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
    
    if not data:
        print("No data found")
        return


    # API 응답에서 데이터 추출
    rows = data.get("SearchSTNTimeTableByFRCodeService", {}).get("row", [])
    print(f"rows len:{len(rows)}")
    if not rows:
        print("No rows found")
        return

    # 중복 검사 및 데이터 삽입 또는 업데이트
    operations = []
    for row in rows:
        filter_key = {
            "FR_CODE": row["FR_CODE"],
            "TRAIN_NO": row["TRAIN_NO"],
            "WEEK_TAG": row["WEEK_TAG"],
            "INOUT_TAG": row["INOUT_TAG"]
        }

        row["subwayId"] = subway_id
        
        update_data = {"$set": row}
        # print(update_data, len(rows))
        # 중복 시 업데이트, 없을 시 삽입
        operations.append(UpdateOne(filter_key, update_data, upsert=True))
    
    # MongoDB에 대량 요청 실행
    if operations:
        result = await collection.bulk_write(operations)
        print(f"{fr_code} {week_tag} {inout_tag} Inserted: {result.upserted_count}, Updated: {result.modified_count}")

inout_tags = ["1","2"] 
week_tags = ["1","2","3"]# week_tag = "1"      # 예시 WEEK_TAG (평일: 1, 토요일: 2, 일요일: 3)
subway_ids = ["1003","1004","1006","1007"] #4호선:15661, 6호선:2068, 7호선:6682
# fr_code_list = ['804','805','806','807','808','809','810','811','812','813','814','815','816','817','818','819','820','821','822','823','824','825','826','827']
# 예제 사용
async def main():
    # subway_id = "1007"
    # fr_code = "818"     # 예시 FR_CODE
   
    for subway_id in subway_ids:
    # inout_tag = "2"     # 예시 INOUT_TAG (상행: 1, 하행: 2)
        mstations = await fetch_metrostation_data(subway_id)
        print(f"{subway_id} mstations len:{len(mstations)}")
        # for fr_code in fr_code_list:
        for metrostation in mstations:
            statnId = metrostation["statnId"]
            fr_code = statnId[7:10]
            for week_tag in week_tags:
                print(f"subway_id:{subway_id} statnId:{statnId} fr_code:{fr_code} week_tag:{week_tag}")
                tasks = [fetch_and_insert(fr_code, week_tag, inout_tag, subway_id) for inout_tag in inout_tags]
                # await fetch_and_insert(fr_code, week_tag, "1")  #상행
                # await fetch_and_insert(fr_code, week_tag, "2")  #하행
                await asyncio.gather(*tasks)


# 이벤트 루프 실행
asyncio.run(main())
