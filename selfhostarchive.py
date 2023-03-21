#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
from downloadpodcast import *
import argparse

app = Flask(__name__)                 # Flask app object

@app.route('/')
def home():  # Flask Home
    return render_template('home.html')



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Flask WebUI, Socket Sender for mGBA')
    parser.add_argument('-wa', '--webaddress', type=str, dest='WEBADDRESS',
                        help='(WebUI) Web address to listen on, default is 0.0.0.0', default="0.0.0.0")
    parser.add_argument('-wp', '--webport', type=int, dest='WEBPORT',
                        help='(WebUI) Web port to listen on, default is 5000', default=5000)

    args = parser.parse_args()

    app.run(host=args.WEBADDRESS, port=args.WEBPORT)
