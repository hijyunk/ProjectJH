from fastapi import FastAPI, HTTPException
from bson.objectid import ObjectId
from pymongo import mongo_client
from wordcloud import WordCloud
from konlpy.tag import Komoran
from gridfs import GridFS
from PIL import Image
import re
import io
import os.path
import pydantic
import json
import requests
import time
import nltk
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'NanumBarunGothic'

pydantic.json.ENCODERS_BY_TYPE[ObjectId] = str

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.relpath("./")))
secret_file = os.path.join(BASE_DIR, '../secret.json')

with open(secret_file) as f:
    secrets = json.loads(f.read())

def get_secret(setting, secrets=secrets):
    try:
        return secrets[setting]
    except KeyError:
        errorMsg = "Set the {} environment variable.".format(setting)
        return errorMsg

HOSTNAME = get_secret("local_mongo_Hostname")
USERNAME = get_secret("local_mongo_Username")
PASSWORD = get_secret("local_mongo_Password")

client = mongo_client.MongoClient(f'mongodb://{USERNAME}:{PASSWORD}@{HOSTNAME}')

db = client['ProjectJH']

def savetomongodb(data):
    collection_name = data['collection']
    collection = db[collection_name]
    
    try:
        # MongoDB에 데이터 삽입
        result = collection.insert_many(data['data'])

        # 삽입된 데이터 조회 (3개까지만)
        inserted_ids = result.inserted_ids
        inserted_data = list(collection.find({"_id": {"$in": inserted_ids}}, {"_id": 0}).limit(3))

        
        mongo_result = {'code':200,
                        'collection':collection_name,
                        'data':inserted_data}
        
        return mongo_result
    
    except Exception as e:
        # 그 외의 예외가 발생하면 서버 오류로 간주합니다.
        raise HTTPException(status_code=500, detail=str(e))

def loadData(collection_name):
    collection = db[collection_name]
    data = list(collection.find({}, {"_id":0}))
    return data

@app.get("/getparkrating")
async def getParkRating(region):
    collection_name = "parkRatings"
    gu = region.split()[-1]
    result = list(db['seoul'].find({"구이름":gu}, {"_id":0}))
    neighborhoods = result[0]["동이름"] if result else []
    
    parks_data = {"code":200, "collection":collection_name, "region":region, "data":[]}
    
    for neighborhood in neighborhoods:
        query = f'공원 in {region} {neighborhood}'
        next_page_token = None
        
        while True:
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {
                'query': query,
                'key': get_secret("google_apiKey"),
                'language': 'ko',
                'pagetoken': next_page_token
            }
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                parks_data['code'] = response.status_code
                raise HTTPException(status_code=response.status_code, detail="Google Maps API error")
            
            results = response.json()
            if 'error_message' in results:
                raise HTTPException(status_code=400, detail=results['error_message'])

            for place in results['results']:
                park_entry = {
                    'name': place.get('name'),
                    'address': place.get('formatted_address'),
                    'rating': place.get('rating', 'Not Available')
                }
                parks_data['data'].append(park_entry)

            next_page_token = results.get('next_page_token')
            if not next_page_token or 'error_message' in results:
                break
            time.sleep(2)

    # 중복 데이터 제거
    unique_addresses = set()
    unique_name = set()
    unique_data = []
    for item in parks_data['data']:
        if item['address'] not in unique_addresses and item['name'] not in unique_name:
            unique_addresses.add(item['address'])
            unique_name.add(item['name'])
            unique_data.append(item)

    parks_data['data'] = unique_data
    
    return savetomongodb(parks_data)

@app.get("/selecttempparks")
def selectTempParks():
    data = loadData("parkRatings")
    
    upper = max(item['rating'] for item in data)
    lower = upper - 0.5
    
    attempt = 0
    while True:
        parks = [item for item in data if upper >= item['rating'] >= lower]
        
        if len(parks) >= 20 or attempt >= 10:
            break
        lower = round(lower - 0.1, 1)
        attempt += 1
    
    temp_data = {'collection':'tempParks', 'data':parks}
    
    return savetomongodb(temp_data)

@app.get("/getparkreviews")
async def getParkReviews():
    tempParks = loadData('tempParks')
    
    park_reviews = []
    
    for place in tempParks:
        # 장소 검색을 위한 URL
        url = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json'
        params = {
            'key': get_secret("google_apiKey"),
            'input': f'{place["name"]} {place["address"]}',
            'inputtype': 'textquery',
            'fields': 'place_id'
            }

        # 장소 검색 요청
        response = requests.get(url, params=params)
        place_data = response.json()
        place_id = place_data['candidates'][0]['place_id']

        # 장소 리뷰를 위한 URL
        review_url = 'https://maps.googleapis.com/maps/api/place/details/json'
        review_params = {
            'key': get_secret("google_apiKey"),
            'language': 'ko',
            'place_id': place_id,
            'fields': 'review'
            }

        # 리뷰 요청
        review_response = requests.get(review_url, params=review_params)
        review_data = review_response.json()

        if len(review_data['result']) > 0:
            # 리뷰 개수
            review_count = len(review_data['result']['reviews'])
            # 리뷰 텍스트
            reviews = [review['text'] for review in review_data['result']['reviews']]
            # 장소 이름과 리뷰를 딕셔너리로 저장
            park_reviews.append({'name':place['name'], 'rating':place['rating'], 'numberOfReviews':review_count, 'reviews':reviews})
        else:
            break

    result = {'code':200, 'collection':'parkReviews', 'data':park_reviews}
    return savetomongodb(result)

@app.get("/selectTop3Parks")
async def selecttop3parks():
    review_data = loadData('parkReviews')
    review_data = [i for i in review_data if i['numberOfReviews']>4]
    review_data.sort(key=lambda x:(x['rating'], x['numberOfReviews']), reverse=True)
    review_data = review_data[:3]
    
    result = {'code':200, 'collection':'top3Parks', 'data':review_data}
    
    return savetomongodb(result)

@app.post("/createWC")
async def createwc():
    collection = db['top3Parks']
    review_data = list(collection.find({}))
    
    komo = Komoran(userdic='user_dic.txt')
    stop_word_file = 'stopwords.txt'
    stop_file = open(stop_word_file, 'rt', encoding='utf-8')
    stop_words = [word.strip() for word in stop_file.readlines()]
    
    fontpath = 'NanumBarunGothic.ttf'
    
    img_list = []
    
    fs = GridFS(db)
    
    for item in review_data:
        text = ' '.join(item['reviews'])
        text = text.replace('\n', '')
        text = re.sub('[^가-힣\s]', '', text)
        
        token = komo.nouns(text)
        
        token = [word for word in token if word not in stop_words]
        
        ko = nltk.Text(tokens=token)
        
        words = ko.vocab().most_common(500)
        wordList = []
        
        for word, count in words:
            if (count >= 1) and (len(word) > 1):
                wordList.append((word, count))
        
        wordcloud = WordCloud(font_path=fontpath, relative_scaling=0.2, background_color='white', colormap='Set3', contour_width=10, contour_color='steelblue')
        
        wordcloud = wordcloud.generate_from_frequencies(dict(wordList))
        wordcloud = wordcloud.to_image()
        
        park_name = item['name']
        filename = f'{park_name}_ReviewWC.png'
    
        img_byte_array = io.BytesIO()
        wordcloud.save(img_byte_array, format='PNG')
        img_byte_array.seek(0)
        
        try:
            fs.delete(item['_id'])
        except:
            pass
        
        fs.put(img_byte_array, _id=item['_id'], filename=filename)
        
        img_list.append({'parkName':park_name, 'fileName':filename, 'fileId':str(item['_id'])})
    
    result = {'code':200, 'data':img_list}
    return result

@app.get("/")
def read_root():
    return {"Hello" : "World"}