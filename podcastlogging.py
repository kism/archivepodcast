"""Specifically this is just common logging functions for both archive programs"""
import logging

LOGLEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LOGLEVELSSTRING = ""
for logginglevel in LOGLEVELS:
    LOGLEVELSSTRING = LOGLEVELSSTRING + logginglevel + " "


def setup_logger(args):
    """APP LOGGING"""
    invalid_log_level = False
    loglevel = logging.INFO
    if args.loglevel:
        args.loglevel = args.loglevel.upper()
        if args.loglevel in LOGLEVELS:
            loglevel = args.loglevel
        else:
            invalid_log_level = True

    logging.basicConfig(
        format="%(asctime)s:%(levelname)s:%(name)s:%(message)s", level=loglevel
    )

    if args.production:
        logging.getLogger("waitress").setLevel(logging.INFO)

    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger()
    formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s:%(message)s")

    try:
        if args.logfile:
            filehandler = logging.FileHandler(args.logfile)
            filehandler.setFormatter(formatter)
            logger.addHandler(filehandler)
    except IsADirectoryError as exc:
        err = "You are trying to log to a directory, try a file"
        raise IsADirectoryError(err) from exc

    except PermissionError as exc:
        err = "The user running this does not have access to the file: " + args.logfile
        raise IsADirectoryError(err) from exc

    logging.info("---")
    logging.info("Logger started")
    if invalid_log_level:
        logging.warning(
            "Invalid logging level: %s, defaulting to INFO", {args.loglevel}
        )
