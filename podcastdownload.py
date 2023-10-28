"""Set of functions to download podcasts to a directory"""
# and return xml that can be served to download them

import xml.etree.ElementTree as Et
import os
import logging
import re
from urllib.error import HTTPError
from datetime import datetime

import requests

try:
    logging.debug("Trying to load pydub w/ffmpeg")
    from pydub import AudioSegment

    logging.info(
        "If if there is a warning about ffmpeg above, install ffmpeg, or remove pydub"
    )
    HASPYDUB = True
except ImportError:
    logging.warning("Pydub not found")
    logging.warning(
        "Optional for when a podcast runner is dumb enough to accidently upload a wav."
    )
    logging.warning("Pydub also requires ffmpeg to installed\n")
    logging.warning("It should have installed if you are using pipenv")
    HASPYDUB = False


imageformats = [".webp", ".png", ".jpg", ".jpeg", ".gif"]
audioformats = [".mp3", ".wav", ".m4a", ".flac"]


def handle_wav(url, title, settingsjson, podcast, extension="", filedatestring=""):
    """Convert podcasts that have wav episodes :/"""
    newlength = 0
    spacer = ""
    if filedatestring != "":
        spacer = "-"
    wavfilepath = (
        settingsjson["webroot"]
        + "content/"
        + podcast["podcastnameoneword"]
        + "/"
        + filedatestring
        + spacer
        + title
        + ".wav"
    )

    mp3filepath = (
        settingsjson["webroot"]
        + "content/"
        + podcast["podcastnameoneword"]
        + "/"
        + filedatestring
        + spacer
        + title
        + ".mp3"
    )

    # If we need do download and convert a wav there is a small chance
    # the user has had ffmpeg issues, remove existing files to play it safe
    if os.path.exists(wavfilepath):
        os.remove(wavfilepath)
        os.remove(mp3filepath)

    # if the asset hasn't already been downloaded and converted
    if not os.path.isfile(mp3filepath):
        if HASPYDUB:
            download_asset(url, title, settingsjson, podcast, extension, filedatestring)

            logging.info("Converting episode %s to mp3", title)
            sound = AudioSegment.from_wav(wavfilepath)
            sound.export(mp3filepath, format="mp3")
            logging.info("Done")

            # Remove wav since we are done with it
            logging.info("Removing wav version of %s", title)
            if os.path.exists(wavfilepath):
                os.remove(wavfilepath)
            logging.info("Done")

        else:
            if not HASPYDUB:
                logging.error("pydub pip package not installed")

            logging.error("Cannot convert wav to mp3!")

    newlength = os.stat(mp3filepath).st_size

    return newlength


def download_asset(url, title, settingsjson, podcast, extension="", filedatestring=""):
    """Download asset from url with appropiate file name"""
    spacer = ""
    if filedatestring != "":
        spacer = "-"

    filepath = (
        settingsjson["webroot"]
        + "content/"
        + podcast["podcastnameoneword"]
        + "/"
        + filedatestring
        + spacer
        + title
        + extension
    )

    if not os.path.isfile(filepath):  # if the asset hasn't already been downloaded
        try:
            logging.debug("Downloading: %s", url)
            logging.info("Downloading asset to: %s", filepath)
            headers = {"user-agent": "Mozilla/5.0"}
            req = requests.get(url, headers=headers, timeout=5)

            if req.status_code == 200:
                with open(filepath, "wb") as assetfile:
                    assetfile.write(req.content)
                    logging.info("Success!")
            else:
                logging.info("HTTP ERROR: %s", str(req.content))

        except HTTPError as err:
            logging.info("Download Failed %s", str(err))

    else:
        logging.debug("Already downloaded: " + title + extension)


def cleanup_file_name(filename):
    """Standardise naming, generate a slug"""
    filename = filename.encode("ascii", "ignore")
    filename = filename.decode()

    # Standardise
    filename = filename.replace("[AUDIO]", "")
    filename = filename.replace("[Audio]", "")
    filename = filename.replace("[audio]", "")
    filename = filename.replace("AUDIO", "")
    filename = filename.replace("(Audio Only)", "")
    filename = filename.replace("(Audio only)", "")
    filename = filename.replace("Ep. ", "Ep ")
    filename = filename.replace("Ep: ", "Ep ")
    filename = filename.replace("Episode ", "Ep ")
    filename = filename.replace("Episode: ", "Ep ")

    # Generate Slug, everything that isnt alphanumeric is now a hyphen, TODO tolower?
    filename = re.sub(r"[^a-zA-Z0-9-]", " ", filename)

    # Remove excess spaces
    while "  " in filename:
        filename = filename.replace("  ", " ")

    # Replace spaces with hyphens
    filename = filename.strip()
    filename = filename.replace(" ", "-")

    logging.debug("Clean Filename: '%s'", filename)
    return filename


def download_podcasts(podcast, settingsjson):
    """Parse the XML, Download all the assets"""
    response = None

    # lets fetch the original podcast xml
    request = podcast["podcasturl"]

    try:
        response = requests.get(request, timeout=5)
    except ValueError:  # NameResolutionError ?
        logging.info("Real early failure on grabbing the podcast xml, weird")
        return

    if response is not None:
        if response.status_code not in (200, 400):
            logging.info(
                "Not a great web request, we got: %s", str(response.status_code)
            )
            return
        else:
            logging.debug("We got a pretty real response by the looks of it")
            logging.debug(str(response))
    else:
        logging.info("Failure, no sign of a response.")
        logging.debug(
            "Probably an issue with the code. Or cloudflare ruining our day maybe?"
        )
        return

    # We have the xml
    podcastxml = Et.fromstring(response.content)
    logging.info("Processing Podcast XML")
    logging.debug(str(podcastxml))

    xmlfirstchild = podcastxml[0]

    # It's time to iterate, we overwrite as necessary from the settings in settings.json
    title = ""
    url = ""

    for channel in xmlfirstchild:  # Dont complain
        logging.debug("Found XML item")
        logging.debug("XML tag: %s", channel.tag)

        # Handle URL, override
        if channel.tag == "link":
            logging.debug("Podcast link: %s", str(channel.text))
            channel.text = settingsjson["inetpath"]

        # Handle Podcast Title, override
        elif channel.tag == "title":
            logging.info("Podcast title: %s", str(channel.text))
            if podcast["podcastnewname"] == "":
                podcast["podcastnewname"] = channel.text
            channel.text = podcast["podcastnewname"]

        # Handle Podcast Description, override
        elif channel.tag == "description":
            logging.debug("Podcast description: %s", str(channel.text))
            channel.text = podcast["podcastdescription"]

        # Remake Atom Tags
        elif channel.tag == "{http://www.w3.org/2005/Atom}link":
            channel.attrib["href"] = (
                settingsjson["inetpath"] + "rss/" + podcast["podcastnameoneword"]
            )
            channel.text = " "  # here me out...

        # Remake Apple Tags
        elif channel.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}owner":
            for child in channel:
                if child.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}name":
                    if podcast["podcastnewname"] == "":
                        podcast["podcastnewname"] = child.text
                    child.text = podcast["podcastnewname"]
                if child.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}email":
                    if podcast["contactemail"] == "":
                        podcast["contactemail"] = child.text
                    child.text = podcast["contactemail"]

        elif channel.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}author":
            if podcast["podcastnewname"] == "":
                podcast["podcastnewname"] = channel.text
            channel.text = podcast["podcastnewname"]

        elif channel.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}new-feed-url":
            channel.text = (
                settingsjson["inetpath"] + "rss/" + podcast["podcastnameoneword"]
            )

        elif channel.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}image":
            if podcast["podcastnewname"] == "":
                podcast["podcastnewname"] = channel.text
            title = podcast["podcastnewname"]
            title = cleanup_file_name(title)
            url = channel.attrib.get("href")
            if url is None:
                url = ""

            for filetype in imageformats:
                if filetype in url:
                    download_asset(url, title, settingsjson, podcast, filetype)
                    channel.attrib["href"] = (
                        settingsjson["inetpath"]
                        + "content/"
                        + podcast["podcastnameoneword"]
                        + "/"
                        + title
                        + filetype
                    )

            channel.text = " "

        # Handle Image
        elif channel.tag == "image":
            for child in channel:
                logging.debug("image > XML tag: %s", child.tag)
                if child.tag == "title":
                    logging.debug("Title: %s", str(child.text))
                    child.text = podcast["podcastnewname"]

                elif child.tag == "link":
                    child.text = settingsjson["inetpath"]

                elif child.tag == "url":
                    title = podcast["podcastnewname"]
                    title = cleanup_file_name(title)
                    url = child.text
                    # Default to prevent unchanged url on error
                    child.text = ""
                    if url is None:
                        url = ""

                    for filetype in imageformats:
                        if filetype in url:
                            download_asset(url, title, settingsjson, podcast, filetype)
                            child.text = (
                                settingsjson["inetpath"]
                                + "content/"
                                + podcast["podcastnameoneword"]
                                + "/"
                                + title
                                + filetype
                            )
                        # else:
                        #     logging.info("Skipping non image file:" + title)

                else:
                    logging.debug(
                        "Unhandled XML tag %s, (under child.tag) leaving as-is",
                        child.tag,
                    )

            channel.text = " "  # here me out...

        # Handle Episode
        elif channel.tag == "item":
            filedatestring = "00000000"

            # Episode Date, need to do this before dealing with real data
            for child in channel:
                if child.tag == "pubDate":
                    originaldate = str(child.text)
                    filedate = datetime(1970, 1, 1)
                    try:
                        filedate = datetime.strptime(
                            originaldate, "%a, %d %b %Y %H:%M:%S %Z"
                        )
                    except ValueError:
                        pass
                    try:
                        filedate = datetime.strptime(
                            originaldate, "%a, %d %b %Y %H:%M:%S %z"
                        )
                    except ValueError:
                        pass
                    filedatestring = filedate.strftime("%Y%m%d")

            for child in channel:
                logging.debug("item > XML tag: %s", child.tag)
                # Episode Title
                if child.tag == "title":
                    title = str(child.text)
                    logging.debug("Title: %s", title)

                # Episode Content (Enclosure)
                elif (
                    child.tag == "enclosure"
                    or "{http://search.yahoo.com/mrss/}content" in child.tag
                ):
                    title = cleanup_file_name(title)
                    url = child.attrib.get("url")
                    # Default to prevent unchanged url on error
                    child.attrib["url"] = ""
                    if url is None:
                        url = ""
                    for audioformat in audioformats:
                        if audioformat in url:
                            if audioformat == ".wav":
                                # Download the wav, and get the new length of the file for the xml
                                newlength = handle_wav(
                                    url,
                                    title,
                                    settingsjson,
                                    podcast,
                                    audioformat,
                                    filedatestring,
                                )
                                audioformat = ".mp3"
                                child.attrib["type"] = "audio/mpeg"
                                # Recalculate file size for the xml
                                child.attrib["length"] = str(newlength)

                            else:
                                download_asset(
                                    url,
                                    title,
                                    settingsjson,
                                    podcast,
                                    audioformat,
                                    filedatestring,
                                )
                            # Set path of audio file
                            child.attrib["url"] = (
                                settingsjson["inetpath"]
                                + "content/"
                                + podcast["podcastnameoneword"]
                                + "/"
                                + filedatestring
                                + "-"
                                + title
                                + audioformat
                            )

                # Episode Image
                elif child.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}image":
                    title = cleanup_file_name(title)
                    url = child.attrib.get("href")
                    if url is None:
                        url = ""
                    for filetype in imageformats:
                        if filetype in url:
                            download_asset(
                                url,
                                title,
                                settingsjson,
                                podcast,
                                filetype,
                                filedatestring,
                            )
                            # Set path of image
                            child.attrib["href"] = (
                                settingsjson["inetpath"]
                                + "content/"
                                + podcast["podcastnameoneword"]
                                + "/"
                                + filedatestring
                                + "-"
                                + title
                                + filetype
                            )

                else:
                    logging.debug(
                        "Unhandled XML tag %s, (under child.tag) leaving as-is",
                        child.tag,
                    )

        else:
            logging.debug(
                "Unhandled XML tag %s, (under channel.tag) leaving as-is", channel.tag
            )

    podcastxml[0] = xmlfirstchild

    tree = Et.ElementTree(podcastxml)
    # These make the name spaces appear nicer in the generated XML
    Et.register_namespace(
        "googleplay", "http://www.google.com/schemas/play-podcasts/1.0"
    )
    Et.register_namespace("atom", "http://www.w3.org/2005/Atom")
    Et.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    Et.register_namespace("media", "http://search.yahoo.com/mrss/")
    Et.register_namespace("sy", "http://purl.org/rss/1.0/modules/syndication/")
    Et.register_namespace("content", "http://purl.org/rss/1.0/modules/content/")
    Et.register_namespace("wfw", "http://wellformedweb.org/CommentAPI/")
    Et.register_namespace("dc", "http://purl.org/dc/elements/1.1/")
    Et.register_namespace("slash", "http://purl.org/rss/1.0/modules/slash/")
    Et.register_namespace("rawvoice", "http://www.rawvoice.com/rawvoiceRssModule/")
    Et.register_namespace("spotify", "http://www.spotify.com/ns/rss/")
    Et.register_namespace("feedburner", "http://rssnamespace.org/feedburner/ext/1.0")

    return tree
