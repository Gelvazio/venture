import os
import json
import hmac
from hashlib import sha1
from flask import Flask, request, redirect, jsonify

app = Flask(__name__)

FB_APP_SECRET = os.environ['FB_APP_SECRET']
FB_VALIDATION_TOKEN = os.environ['FB_VALIDATION_TOKEN']
FB_PAGE_ACCESS_TOKEN = os.environ['FB_PAGE_ACCESS_TOKEN']

@app.route('/')
def main():
    return redirect('/index')

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
                    received(event)
                elif 'optin' in event:
                    auth(event)
                elif 'postback' in event:
                    postback(event)
                else:
                    print('Bad event, returning')
                    return '', 404

    return ''

if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', '8080')))
