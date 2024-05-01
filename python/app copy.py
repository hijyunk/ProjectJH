from fastapi import FastAPI, HTTPException
from bson.objectid import ObjectId
from pymongo import mongo_client, UpdateOne
from wordcloud import WordCloud
from konlpy.tag import Komoran
from gridfs import GridFS
from PIL import Image
import mysql.connector
from mysql.connector import Error
import re
import copy
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

MONGO_HOSTNAME = get_secret("local_mongo_Hostname")
MONGO_USERNAME = get_secret("local_mongo_Username")
MONGO_PASSWORD = get_secret("local_mongo_Password")

client = mongo_client.MongoClient(f'mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOSTNAME}')
db = client['ProjectJH']

# MongoDB에 데이터 저장하기
def savetomongodb(data):
    collection_name = data['collection']
    collection = db[collection_name]
    
    try:
        operations = []
        for item in data['data']:
            update_operation = UpdateOne(
                {'place_id':item['place_id']},
                {'$set': item},
                upsert=True
            )
            operations.append(update_operation)
        
        collection.bulk_write(operations)

        # 삽입된 데이터 조회 (3개까지만)
        place_ids = [item['place_id'] for item in data['data']]
        inserted_data = list(collection.find({"place_id": {"$in": place_ids}}, {"_id": 0}).limit(3))

        
        mongo_result = {'code':200,
                        'collection':collection_name,
                        'data':inserted_data}
        
        return mongo_result
    
    except Exception as e:
        # 그 외의 예외가 발생하면 서버 오류로 간주합니다.
        raise HTTPException(status_code=500, detail=str(e))

# MongoDB에서 데이터 불러오기 
def loadData(collection_name):
    collection = db[collection_name]
    data = list(collection.find({}, {"_id":0}))
    return data

# mysql 연결하기
MYSQL_HOSTNAME = get_secret("Mysql_Hostname")
MYSQL_PORT = get_secret("Mysql_Port")
MYSQL_USERNAME = get_secret("Mysql_Username")
MYSQL_PASSWORD = get_secret("Mysql_Password")
MYSQL_DBNAME = get_secret("Mysql_DBname")

connection = mysql.connector.connect(host = MYSQL_HOSTNAME, 
                                     port = MYSQL_PORT,
                                     user = MYSQL_USERNAME,
                                     password = MYSQL_PASSWORD,
                                     database = MYSQL_DBNAME)

# mysql에 데이터 저장하기
def savetomysql(table_name, data):
    cursor = connection.cursor()
    try:
        # 새 데이터 저장 
        for entry in data:
            columns = ', '.join(entry.keys())
            placeholders = ', '.join(['%s'] * len(entry))
            update_clause = ', '.join([f"{key} = VALUES({key})" for key in entry.keys()])
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"
            cursor.execute(query, [entry[col] for col in entry])
        connection.commit()
    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if connection.is_connected():
            cursor.close()

def loadfrommysql(table_name):
    cursor = connection.cursor(dictionary=True)
    try:
        select_query = f'SELECT * FROM {table_name}'
        cursor.execute(select_query)
        result = cursor.fetchall()
        return result
    except Error as e:
        print("Error while fetching data from MySQL", e)
    finally:
        if connection.is_connected(): cursor.close()

global_region = None

def checkfrommysql(table_name, field, region):
    cursor = connection.cursor()
    try:
        query = f"SELECT EXISTS(SELECT 1 FROM {table_name} WHERE {field} = %s)"
        cursor.execute(query, (region,))
        result = cursor.fetchone()
        return result[0] == 1
    except Error as e:
        print(f"Error while checking condition in MySQL: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# 모든 공원 별점 가져오기 
def getParkRating(region):
    global global_region
    global_region = region
    gu = global_region.split()[-1]
    
    check = checkfrommysql("history", "region", gu)
    
    savetomysql('history', [{'region':gu}])
    
    #return savetomongodb(parks_data)


def getParkReviews():
    tempParks = loadData('tempParks')
    collection_name = 'parkReviews'
    
    park_reviews = []
    for place in tempParks[:10]:
        place_id = place['place_id']
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
            # 리뷰 텍스트
            reviews = [review['text'] for review in review_data['result']['reviews'] if len(review['text']) > 10]
            # 리뷰 개수
            review_count = len(reviews)
            # 장소 이름과 리뷰를 딕셔너리로 저장
            park_reviews.append({'region':place['region'],'place_id':place_id,'name':place['name'], 'rating':place['rating'], 'numberOfReviews':review_count, 'reviews':reviews})
        else:
            break

    result = {'code':200, 'collection':collection_name, 'data':park_reviews}
    return result
    #return savetomongodb(result)

def selecttop3parks():
    review_data = loadData('parkReviews')
    # 리뷰 개수가 4개 이상
    review_data = [i for i in review_data if i['numberOfReviews']>=4]
    # 별점과 리뷰 개수로 내림차순
    review_data.sort(key=lambda x:(x['rating'], x['numberOfReviews']), reverse=True)
    # 상위 3개
    review_data = review_data[:3]
    
    result_all = {'code':200, 'collection':'top3Parks', 'data':review_data}
    result = copy.deepcopy(result_all)
    
    for park in result['data']:
        text = park['reviews'][0].replace('\n', ' ')
        if len(text) > 100:
            text = text[:100]+'...'
        park['reviews'] = text
    
    savetomysql(result)
    
    return result_all

gu = "서초구" 
collection = db["parkReviews"]
check_data = collection.find_one({"region": gu}) is not None
#print(check_data)

# collection = db['top3Parks']
# review_data = list(collection.find({}))
# for item in review_data:
#     print(item['region'])

# review_data = loadData('parkReviews')
# collection_name = 'top3Parks'

# print(review_data[1])
# print()
# print()

# review_data.sort(key=lambda x:(x['rating'], x['numberOfReviews']), reverse=True)
# review_data = review_data[:3]
# result_all = {'code':200, 'collection':collection_name, 'data':review_data}
# result = copy.deepcopy(result_all)

# for park in result['data']:
#     text = park['reviews'][0].replace('\n', ' ')
#     if len(text) > 100:
#         text = text[:100]+'...'
#     park['reviews'] = text

# print(result['data'])

# savetomysql(collection_name, result['data'])

def createwc():
    gu = "서울시 강남구"
    collection_name = "wcHistory"
    collection = db[collection_name]
    check = collection.find_one({"region": gu}) is not None
    
    if check:
        return
    else:
        collection_name = "wcHistory"
        collection = db[collection_name]
        check = collection.find_one({"region": gu}) is not None


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
            
            data_to_save = {
                'collection': 'wordclouds',
                'data': [{
                    'place_id': item['place_id'],
                    'park_name': park_name,
                    'filename': filename,
                    'image_data': img_byte_array.getvalue()
                }]
            }
            
            savetomysql('wordclouds', data_to_save['data'])
            
            try:
                fs.delete(item['_id'])
            except:
                pass
            
            fs.put(img_byte_array, _id=item['_id'], filename=filename)
            
            img_list.append({'place_id':item['place_id'], 'parkName':park_name, 'fileName':filename, 'fileId':str(item['_id'])})
            
        result = {'code':200, 'collection':collection_name, 'region':gu, 'data':img_list}
        return savetomongodb(result)

# a = createwc()
# print(a)

a = loadfrommysql('top3Parks')
print(a)