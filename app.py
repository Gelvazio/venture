# encoding: utf-8

from __future__ import print_function

import os
import json
import hmac
from hashlib import sha1
from decimal import Decimal

import requests
from requests.exceptions import RequestException
from flask import Flask, request, redirect, jsonify
from yahoo_finance import Share, YQLQueryError

app = Flask(__name__)

FB_APP_SECRET = os.environ['FB_APP_SECRET']
FB_VALIDATION_TOKEN = os.environ['FB_VALIDATION_TOKEN']
FB_PAGE_ACCESS_TOKEN = os.environ['FB_PAGE_ACCESS_TOKEN']

STOCK_FMT = u"""
{Name} ({Symbol}):
  Bolsa: {StockExchange}
  Valor de Mercado: {MarketCapitalization}
  Volume de ações: {Volume}
  Valor de abertura (por ação): {Open}{Currency}
  Valor atual (por ação): {Open}{Currency} ({ChangeinPercent})
  Comparação com a média recente: {PercentChangeFromFiftydayMovingAverage}
""".strip()

def get_stock_info(symbol):
    try:
        share = Share(symbol)
    except YQLQueryError:
        return None, None

    name = share.data_set.get('Name')
    if not name:
        return None, None
    
    return STOCK_FMT.format(**share.data_set), name


conversations = {}


class Conversation(object):
    
    WELCOME_MESSAGE = """
Olá! Seu patrocinador João da Silva disponibilizou R$ 1500,00.
Tenho sugestões para você investir esta quantia!
Digite o nome da empresa para investir ou digite ? para sugestões.
"""
    ASK_FOR_COMPANY = "Digite o nome da empresa para investir ou digite ? para sugestões."
    HOW_MUCH_MESSAGE = "Quanto deseja investir?"
    CONFIRM_TRANSACTION = "Confirma o investimento de {}USD na empresa {}?"
    TRANSACTION_COMPLETE = "Ok, investido {}USD na empresa {}!"
    WRONG_QUESTION = "O que é Câmbio Flutuante?"
    MENTOR_MESSAGE = """
Para responder suas dúvidas temos o seguinte mentor, que pode tirar todas as dúvidas!
Pedro Alves
Tel: 123123123
"""
    INVEST_MORE = "Deseja investir mais?"
    BYE_MESSAGE = "Qualquer coisa, só me mandar uma mensagem! Obrigado :)"
    WRONG_COMPANY = "Não pude localizar essa empresa, tente novamente"
    SUGGESTIONS = ['AAPL', 'GOOG']

    def __init__(self):
        self.state = 0
        self.value = 0
        self.company = None

    def process_message(self, message):
        if self.state == 0:
            self.state = 1
            return self.WELCOME_MESSAGE
        elif self.state == 1:
            if message == "?":
                self.state = 3

                msg = []
                for sym in self.SUGGESTIONS:
                    info, name = get_stock_info(sym)
                    if info:
                        if len(info) > 320:
                            msg.extend(info.split('\n'))
                        else:
                            msg.append(info)
                msg.append('Responda com a sigla da empresa')
                return msg
            
            info, name = get_stock_info(sym)
            if not info:
                return self.WRONG_COMPANY

            self.company = name
            self.state = 2
            return info
        elif self.state == 2:
            self.value = Decimal(message)
            self.state = 4
            return self.CONFIRM_TRANSACTION.format(self.value, self.company)
        elif self.state == 3:
            self.company = message
            self.state = 2
            return self.HOW_MUCH_MESSAGE
        elif self.state == 4:
            if message == "Sim":
                self.state = 5
                return [self.TRANSACTION_COMPLETE.format(self.value, self.message), self.INVEST_MORE]
            else:
                self.state = 0
                self.value = 0
                self.company = None
                return self.ASK_FOR_COMPANY
        elif self.state == 5:
            self.state = 0
            if message == "Sim":
                return self.ASK_FOR_COMPANY
            else:
                return self.BYE_MESSAGE


def parse_webhook():
    signature = request.headers.get('x-hub-signature')
    if not signature:
        return None

    method, hsh = signature.split('=', 1)
    mac = hmac.new(FB_APP_SECRET, request.get_data(), sha1)
    if mac.hexdigest().lower() != hsh.lower():
        return None

    try:
        return request.json
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
    if isinstance(text, list):
        for t in text:
            r = send_msg(dest, {'text': t})

        return r
    else:
        return send_msg(dest, {'text': text})


def auth(event):
    if send_text(event['sender']['id'], 'Authentication successful'):
        return '', 200

    return '', 400

def received(event):
    sender_id = event['sender']['id']
    if sender_id not in conversations:
        conversations[sender_id] = Conversation()
    conversation = conversations[sender_id]
    message = event['message'].get('text')

    if not message or \
       send_text(event['sender']['id'], conversation.process_message(message)):
        return '', 200

    return '', 400    

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and \
           request.args.get('hub.verify_token') == FB_VALIDATION_TOKEN:
            return request.args.get('hub.challenge')
        else:
            return '', 403

    data = parse_webhook()
    if not data:
        return '', 400
    
    print('data:', data)

    if data['object'] == 'page':
        for entry in data['entry']:
            for event in entry['messaging']:
                if 'message' in event and not event['message'].get('is_echo'):
                    received(event)
                elif 'optin' in event:
                    return auth(event)
                elif 'postback' in event:
                    pass #postback(event)
                else:
                    print('Unknown event, returning')
                    return '', 200

    return '', 200

def teste():
    conversation = Conversation()
    print(conversation.process_message("Oi"))
    print(conversation.process_message("?"))
    print(conversation.process_message("APPLE"))
    print(conversation.process_message("600"))
    print(conversation.process_message("Sim"))
    print(conversation.process_message("Não"))

if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', '8080')))
    #teste()
