import os
import json
import hmac
from hashlib import sha1

import requests
from requests.exceptions import RequestException
from flask import Flask, request, redirect, jsonify

app = Flask(__name__)

FB_APP_SECRET = os.environ['FB_APP_SECRET']
FB_VALIDATION_TOKEN = os.environ['FB_VALIDATION_TOKEN']
FB_PAGE_ACCESS_TOKEN = os.environ['FB_PAGE_ACCESS_TOKEN']

def parse_webhook():
    signature = request.headers.get('x-hub-signature')
    if not signature:
        return None

    method, hsh = signature.split('=', 1)
    mac = hmac.new(APP_SECRET, request.body, sha1)
    if mac.hexdigest().lower() != hsh.lower():
        return None

    try:
        return json.loads(request.body) 
    except json.DecodeError:
        return None

def send_msg(dest, msg):
    data = {
        'recipient': {'id': dest},
        'message': msg
    }

    url = 'https://graph.facebook.com/v2.6/me/messages?access_token={}'.format(FB_PAGE_ACCESS_TOKEN)

    try:
        r = requests.post(url, json=data)
        if r.status_code != 200:
            print('Send failed:', r.json())
            return None

        return r.json()
    except (RequestException, ValueError) as e:
        print('Send failed:', e)
        return None

def send_text(dest, text):
    return send_msg(dest, {'text': text})

def auth(event):
    if send_text(event['sender']['id'], 'Authentication successful'):
        return '', 200

    return '', 400

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and \
           request.args.get('hub.verify_token') == FB_VALIDATION_TOKEN:
            return req.args.get('hub.challenge')
        else:
            return '', 403

    data = parse_webhook()
    if not data:
        return '', 400
    
    if data['object'] == 'page':
        for entry in data['entry']:
            for event in entry['messaging']:
                print('Event:', event)

                if 'message' in event:
                    #received(event)
                elif 'optin' in event:
                    return auth(event)
                elif 'postback' in event:
                    #postback(event)
                else:
                    print('Bad event, returning')
                    return '', 400

    return '', 200

if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', '8080')))
