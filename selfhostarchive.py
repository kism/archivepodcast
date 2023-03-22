#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
from downloadpodcast import *
import argparse

app = Flask(__name__)                 # Flask app object


@app.route('/')
def home():  # Flask Home
    return render_template('home.j2', settingsjson=settingsjson)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Mirror / rehost a podcast, self hoasted with Flask!')
    parser.add_argument('-wa', '--webaddress', type=str, dest='WEBADDRESS',
                        help='(WebUI) Web address to listen on, default is 0.0.0.0', default="0.0.0.0")
    parser.add_argument('-wp', '--webport', type=int, dest='WEBPORT',
                        help='(WebUI) Web port to listen on, default is 5000', default=5000)
    parser.add_argument('-c', type=str, dest='settingspath',
                        help='Config path /path/to/settings.json')
    parser.add_argument('--debug', dest='debug',
                        action='store_true', help='Show debug output')
    args = parser.parse_args()

    loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG
    logging.basicConfig(format='%(levelname)s:%(message)s', level=loglevel)

    args = parser.parse_args()
    settingsjson = get_settings(args)

    app.run(host=args.WEBADDRESS, port=args.WEBPORT)
