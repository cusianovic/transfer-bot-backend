from flask import Flask, Response, request, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from waitress import serve
from apscheduler.schedulers.background import BackgroundScheduler
import json
import pandas
import uuid
import os
from dotenv import load_dotenv
from utils.sse import MessageAnnouncer, format_sse 
from utils.user import User, userList
from utils.chat import UCLAChatBot

load_dotenv()

app = Flask(__name__)

PRODUCTION = os.getenv('PRODUCTION', 'false')

EMBEDDING_CSV_NAME = os.getenv('EMBEDDING_CSV_NAME')
df = pandas.read_csv(f"./dataset/embeddings/{EMBEDDING_CSV_NAME}")

API_KEY = os.getenv('OPENAI_KEY')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL')
LARGE_LANGUAGE_MODEL = os.getenv('LARGE_LANGUAGE_MODEL')


chatbot = UCLAChatBot(API_KEY=os.getenv('OPENAI_KEY'), CHAT_MODEL=LARGE_LANGUAGE_MODEL, EMBEDDING_MODEL=EMBEDDING_MODEL, df=df)

announcer = MessageAnnouncer()

@app.route('/listen', methods=['GET'])
def listen():

    def stream(id):
        messages = announcer.listen(id)

        if id in userList:
            introPacket = json.dumps(userList[id].history)
            announcer.announce(id, format_sse(data=introPacket, event="startup"))
        else:
            announcer.announce(id, format_sse(data=json.dumps([]), event="startup"))


        while True:
            msg = messages.get()
            yield msg
    
    resp = Response()

    resp.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    resp.headers['Access-Control-Allow-Credentials'] = 'true'

    cookie = request.cookies.get('userID')

    # Response needs to finish before cookie is set, if no connection cookie, we close. otherwise, we stream the data

    if cookie == None:
        cookie = str(uuid.uuid4())
        resp.set_cookie(key='userID', value=cookie, samesite=None)
    else:
        resp.mimetype = 'text/event-stream'
        resp.response = stream(cookie)
 
    return resp

@app.route('/query', methods=['POST', 'OPTIONS'])
def query():

    resp = Response()
    resp.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    resp.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    resp.headers.add('Access-Control-Allow-Credentials', 'true')
    resp.headers.add('Access-Control-Allow-Headers', "Content-Type")
    
    if request.method == 'OPTIONS':
        return resp

    userID  = request.cookies.get('userID')

    if userID in userList:
        user = userList[userID] 
    else:
        user = User(userID)

    query = json.loads(request.data)

    if(query):
        action = chatbot.ask(user, query)

    announcer.announce(userID, format_sse(data=action, event="queryResponse"))

    return resp

    
scheduler = BackgroundScheduler()

def ping():
    announcer.globalAnnounce(format_sse(event="ping", data=""))

job = scheduler.add_job(ping, 'interval', seconds=17280)
scheduler.start()

if(PRODUCTION == 'true'):
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )
    serve(app, port=5000, threads=100)
else:
    app.run()