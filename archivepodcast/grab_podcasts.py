

from .logger import get_logger

logger = get_logger(__name__)

def grab_podcasts():
    """Loop through defined podcasts, download and store the xml"""
    for podcast in settingsjson["podcast"]:
        tree = None
        previousfeed = ""
        logger.info("📜 Processing settings entry: %s", podcast["podcastnewname"])

        try:  # If the var exists, we set it
            previousfeed = PODCASTXML[podcast["podcastnameoneword"]]
        except KeyError:
            pass

        rssfilepath = settingsjson["webroot"] + "rss/" + podcast["podcastnameoneword"]

        if podcast["live"] is True:  # download all the podcasts
            try:
                tree = download_podcasts(podcast, settingsjson, s3, s3pathscache)
                # Write xml to disk
                tree.write(
                    rssfilepath,
                    encoding="utf-8",
                    xml_declaration=True,
                )
                logger.debug("Wrote rss to disk: %s", rssfilepath)

            except Exception:  # pylint: disable=broad-exception-caught
                emoji = "❌" # un-upset black
                logger.exception("%s", emoji)
                logger.error(
                    "%s RSS XML Download Failure, attempting to host cached version",
                    emoji,
                )
                tree = None
        else:
            logger.info('📄 "live": false, in settings so not fetching new episodes')

        # Serving a podcast that we can't currently download?, load it from file
        if tree is None:
            logger.info("📄 Loading rss from file: %s", rssfilepath)
            try:
                tree = Et.parse(rssfilepath)
            except FileNotFoundError:
                logger.error("❌ Cannot find rss xml file: %s", rssfilepath)

        if tree is not None:
            PODCASTXML.update(
                {
                    podcast["podcastnameoneword"]: Et.tostring(
                        tree.getroot(),
                        encoding="utf-8",
                        method="xml",
                        xml_declaration=True,
                    )
                }
            )
            logger.info(
                "📄 Hosted: %srss/%s",
                settingsjson["inetpath"],
                podcast["podcastnameoneword"],
            )

            # Upload to s3 if we are in s3 mode
            if (
                settingsjson["storagebackend"] == "s3"
                and previousfeed
                != PODCASTXML[
                    podcast["podcastnameoneword"]
                ]  # This doesn't work when feed has build dates times on it, patreon for one
            ):
                try:
                    # Upload the file
                    s3.put_object(
                        Body=PODCASTXML[podcast["podcastnameoneword"]],
                        Bucket=settingsjson["s3bucket"],
                        Key="rss/" + podcast["podcastnameoneword"],
                        ContentType="application/rss+xml",
                    )
                    logger.info(
                        '📄⛅ Uploaded feed "%s" to s3', podcast["podcastnameoneword"]
                    )
                except Exception:  # pylint: disable=broad-exception-caught
                    logger.exception("⛅❌ Unhandled s3 error trying to upload the file: %s")

        else:
            logger.error("❌ Unable to host podcast, something is wrong")
