"""The arg parser"""

# 🐍 Standard Modules
import argparse

def create_arg_parser():
    """Create an arg parser object"""
    parser = argparse.ArgumentParser(
        description="Mirror / rehost a podcast, self hoasted with Flask!"
    )
    parser.add_argument(
        "-wa",
        "--webaddress",
        type=str,
        dest="webaddress",
        help="(WebUI) Web address to listen on, default is 0.0.0.0",
        default="0.0.0.0",
    )
    parser.add_argument(
        "-wp",
        "--webport",
        type=int,
        dest="webport",
        help="(WebUI) Web port to listen on, default is 5000",
        default=5000,
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        dest="settingspath",
        help="Config path /path/to/settings.json",
    )
    parser.add_argument(
        "--loglevel",
        type=str,
        dest="loglevel",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    parser.add_argument(
        "-lf",
        "--logfile",
        type=str,
        dest="logfile",
        help="Log file full path",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        dest="production",
        help="Run the server with waitress instead of flask debug server",
    )
    return parser
