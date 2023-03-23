#!/usr/bin/env python3
from flask import Flask, render_template, Blueprint
from downloadpodcast import *
import argparse
import time
import threading

app = Flask(__name__)                 # Flask app object


@app.route('/')
def home():  # Flask Home
    return render_template('home.j2', settingsjson=settingsjson)


def podcastloop(settingsjson):
    while True:
        # download all the podcasts
        for podcast in settingsjson['podcast']:
            tree = download_podcasts(settingsjson)
            if tree:
                tree.write(settingsjson['webroot'] + 'rss/' +
                           podcast['podcastnameoneword'], encoding='utf-8', xml_declaration=True)
            else:
                logging.info("XML Write Failure")

        logging.info("Sleeping")
        time.sleep(3600)


def main(args, settingsjson):

    # Start Thread
    thread = threading.Thread(target=podcastloop, args=(settingsjson,))
    thread.start()

    # Finish Creating App
    blueprint = Blueprint('site', __name__, static_url_path='/content',
                          static_folder=settingsjson['webroot'] + "/content")
    app.register_blueprint(blueprint)
    app.run(host=args.WEBADDRESS, port=args.WEBPORT)

    # Cleanup
    thread.join()


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

    main(args, settingsjson)
