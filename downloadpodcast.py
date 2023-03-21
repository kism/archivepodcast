import xml.etree.ElementTree as Et
import requests
import os
import logging
from urllib.error import HTTPError
from datetime import datetime



imageformats = ['.webp', '.png', '.jpg', '.jpeg', '.gif']
audioformats = ['.mp3', '.wav', '.m4a', '.flac']

# Download asset from url with appropiate file name
def download_asset(url, title, settingsjson, podcast, extension='', filedatestring=''):
    spacer = ''
    if filedatestring != '':
        spacer = '-'

    filepath = settingsjson['webroot'] + 'content/' + \
        podcast['podcastnameoneword'] + '/' + \
        filedatestring + spacer + title + extension

    if not os.path.isfile(filepath):  # if the asset hasn't already been downloaded
        if True:
            try:
                logging.info("Downloading: " + url)
                headers = {'user-agent': 'Mozilla/5.0'}
                r = requests.get(url, headers=headers)

                if (r.status_code == 200):
                    with open(filepath, 'wb') as f:
                        f.write(r.content)
                        logging.info("\033[92mSuccess!\033[0m")
                else:
                    logging.info("HTTP ERROR: " + str(r.content))

            except HTTPError as err:
                logging.info("\033[91mDownload Failed\033[0m" + ' ' + str(err))

    else:
        logging.info("Already downloaded: " + title + extension)

# Standardise naming, fix everything that could cause something to be borked on the file system or in a url
def cleanup_file_name(filename):
    filename = filename.encode('ascii', 'ignore')
    filename = filename.decode()

    # Standardise
    filename = filename.replace('[AUDIO]', '')
    filename = filename.replace('[Audio]', '')
    filename = filename.replace('[audio]', '')
    filename = filename.replace('AUDIO', '')
    filename = filename.replace('Ep. ', 'Ep ')
    filename = filename.replace('Ep: ', 'Ep ')
    filename = filename.replace('Episode ', 'Ep ')
    filename = filename.replace('Episode: ', 'Ep ')

    # Generate Slug
    invalidcharacters = ['?', '\\', '/', ':', '*', '"', '$', '<', '>', '(', ')', '|', '&', "'", "_", "[", "]", ".", "#", ";"]

    for invalidcharacter in invalidcharacters:
        filename = filename.replace(invalidcharacter, ' ')

    while '  ' in filename:
        filename = filename.replace('  ', ' ')

    filename = filename.strip()
    filename = filename.replace(' ', '-')

    logging.debug('\033[92mClean Filename\033[0m: ' + "'" + filename + "'")
    return filename

# Parse the XML, Download all the assets
def download_podcasts(settingsjson):
    for podcast in settingsjson['podcast']:
        response = None

        # lets fetch the original podcast xml
        request = podcast['podcasturl']

        try:
            response = requests.get(request, timeout=5)
        except:
            logging.info("Real early failure on grabbing the podcast xml, weird")
            exit(1)

        if response is not None:
            if response.status_code != 200 and response.status_code != 400:
                logging.info("Not a great web request, we got: " + str(response.status_code))
                exit(1)
            else:
                logging.debug("We got a pretty real response by the looks of it")
                logging.debug(str(response))
        else:
            logging.info("Failure, no sign of a response.")
            logging.debug(
                "Probably an issue with the code. Not patreon catching onto you pirating a premium podcast.")
            exit(1)

        # We have the xml
        podcastxml = Et.fromstring(response.content)
        logging.debug(str(podcastxml))

        xmlfirstchild = podcastxml[0]

        # It's time to iterate through the lad, we overwrite as necessary from the settings in settings.json
        title = ''
        url = ''

        for channel in xmlfirstchild:  # Dont complain
            logging.info("\033[47m\033[30mFound XML item \033[0m")
            logging.debug('XML tag: ' + channel.tag)

            # Handle URL, override
            if channel.tag == 'link':
                logging.info("Podcast link: " + str(channel.text))
                channel.text = settingsjson['inetpath']

            # Handle Podcast Title, override
            elif channel.tag == 'title':
                logging.info("Podcast title: " + str(channel.text))
                if podcast['podcastnewname'] == '':
                    podcast['podcastnewname'] = channel.text
                channel.text = podcast['podcastnewname']

            # Handle Podcast Description, override
            elif channel.tag == 'description':
                logging.info("Podcast description: " + str(channel.text))
                channel.text = podcast['podcastdescription']

            # Remake Atom Tags
            elif channel.tag == '{http://www.w3.org/2005/Atom}link':
                channel.attrib['href'] = settingsjson['inetpath'] + 'rss/' + podcast['podcastnameoneword']
                channel.text = ' '  # here me out...

            # Remake Apple Tags
            elif channel.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}owner':
                for child in channel:
                    if child.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}name':
                        if podcast['podcastnewname'] == '':
                            podcast['podcastnewname'] = child.text
                        child.text = podcast['podcastnewname']
                    if child.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}email':
                        if podcast['contactemail'] == '':
                            podcast['contactemail'] = child.text
                        child.text = podcast['contactemail']

            elif channel.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}author':
                if podcast['podcastnewname'] == '':
                    podcast['podcastnewname'] = channel.text
                channel.text = podcast['podcastnewname']

            elif channel.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}image':
                if podcast['podcastnewname'] == '':
                    podcast['podcastnewname'] = channel.text
                title = podcast['podcastnewname']
                title = cleanup_file_name(title)
                url = channel.attrib.get('href')
                if url == None:
                    url = ''

                for filetype in imageformats:
                    if filetype in url:
                        download_asset(url, title, settingsjson, podcast, filetype)
                        channel.attrib['href'] = settingsjson['inetpath'] + 'content/' + podcast['podcastnameoneword'] + '/' + title + filetype

                channel.text = ' '

            # Handle Image
            elif channel.tag == 'image':
                for child in channel:
                    logging.debug('image > XML tag: ' + child.tag)
                    if child.tag == 'title':
                        logging.info("Title: " + str(child.text))
                        child.text = podcast['podcastnewname']

                    elif child.tag == 'link':
                        child.text = settingsjson['inetpath']

                    elif child.tag == 'url':
                        title = podcast['podcastnewname']
                        title = cleanup_file_name(title)
                        url = child.text
                        if url == None:
                            url = ''

                        for filetype in imageformats:
                            if filetype in url:
                                download_asset(url, title, settingsjson, podcast, filetype)
                                child.text = settingsjson['inetpath'] + 'content/' + podcast['podcastnameoneword'] + '/' + title + filetype
                            # else:
                            #     logging.info("Skipping non image file:" + title)

                    else:
                        logging.debug('Unhandled XML tag, leaving as-is')

                channel.text = ' '  # here me out...

            # Handle Episode
            elif channel.tag == 'item':
                filedatestring = '00000000'
                for child in channel:
                    logging.debug('item > XML tag: ' + child.tag)
                    # Episode Title
                    if child.tag == 'title':
                        title = str(child.text)
                        logging.info("Title: " + title)
                    # Episode Date
                    elif child.tag == 'pubDate':
                        originaldate = str(child.text)
                        filedate = datetime(1970, 1, 1)
                        try:
                            filedate = datetime.strptime(originaldate, '%a, %d %b %Y %H:%M:%S %Z')
                        except:
                            pass
                        try:
                            filedate = datetime.strptime(originaldate, '%a, %d %b %Y %H:%M:%S %z')
                        except:
                            pass
                        filedatestring = filedate.strftime("%Y%m%d")

                    # Episode Content (Enclosure)
                    elif child.tag == 'enclosure':
                        title = cleanup_file_name(title)
                        url = child.attrib.get('url')
                        if url == None:
                            url = ''
                        # TODO wav conversion here?
                        for format in audioformats:
                            if format in url:
                                download_asset(url, title, settingsjson, podcast, format, filedatestring)
                                # Set path of audio file
                                child.attrib['url'] = settingsjson['inetpath'] + 'content/' + podcast['podcastnameoneword'] + '/' + title + format

                    # Episode Image
                    elif child.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}image':
                        title = cleanup_file_name(title)
                        url = child.attrib.get('href')
                        if url == None:
                            url = ''
                        for filetype in imageformats:
                            if filetype in url:
                                download_asset(url, title, settingsjson, podcast, filetype, filedatestring)
                                # Set path of image
                                child.attrib['href'] = settingsjson['inetpath'] + 'content/' + podcast['podcastnameoneword'] + '/' + title + filetype
                    # Episode Audio, TODO WHAT IS THIS YAHOO BULLSHIT, DO I NEED IT????
                    # elif child.tag == '{http://search.yahoo.com/mrss/}content':
                    #     title = cleanup_file_name(title)
                    #     url = child.attrib.get('url')
                    #     if url == None:
                    #         url = ''
                    #     # TODO wav conversion here?
                    #     for format in audioformats:
                    #         if format in url:
                    #             download_asset(url, title, settingsjson, podcast, format, filedatestring)
                    #             # Set path of audio file
                    #             child.attrib['url'] = settingsjson['inetpath'] + 'content/' + podcast['podcastnameoneword'] + '/' + title + format

                    else:
                        logging.debug('Unhandled XML tag, leaving as-is')

            else:
                logging.debug('Unhandled XML tag, leaving as-is')

        podcastxml[0] = xmlfirstchild

        tree = Et.ElementTree(podcastxml)
        # These make the name spaces appear nicer in the generated XML
        Et.register_namespace('googleplay', 'http://www.google.com/schemas/play-podcasts/1.0')
        Et.register_namespace('atom',       'http://www.w3.org/2005/Atom')
        Et.register_namespace('itunes',     'http://www.itunes.com/dtds/podcast-1.0.dtd')
        Et.register_namespace('media',      'http://search.yahoo.com/mrss/')
        Et.register_namespace('sy',         'http://purl.org/rss/1.0/modules/syndication/')
        Et.register_namespace('content',    'http://purl.org/rss/1.0/modules/content/')
        Et.register_namespace('wfw',        'http://wellformedweb.org/CommentAPI/')
        Et.register_namespace('dc',         'http://purl.org/dc/elements/1.1/')
        Et.register_namespace('slash',      'http://purl.org/rss/1.0/modules/slash/')
        Et.register_namespace('podcast',    'https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/1.0.md')
        Et.register_namespace('rawvoice',   'http://www.rawvoice.com/rawvoiceRssModule/')
        Et.register_namespace('spotify',    'http://www.spotify.com/ns/rss/')
        Et.register_namespace('feedburner', 'http://rssnamespace.org/feedburner/ext/1.0')

        return tree