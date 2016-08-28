import os
from flask import Flask, request, redirect


app = Flask(__name__)

@app.route('/')
def main():
  return redirect('/index')

@app.route('/index')
def index():
  return 'Hello, World!'

if __name__ == '__main__':
  app.run(port=int(os.environ.get('PORT', '8080')))
