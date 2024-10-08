# #!/usr/bin/env python3
# """Self hosted podcast archiver"""

# # 🐍 Standard Modules
# import os
# import signal
# import sys

# from .logger import get_logger

# logger = get_logger(__name__)

# def reload_settings(signalNumber, frame):
#     """Handle Sighup"""
#     global settingsjson
#     settingserror = False
#     logger.debug("Handle Sighup %s %s", signalNumber, frame)
#     logger.info("🙋 Got SIGHUP, Reloading Config")

#     try:
#         settingsjson = get_settings(args)
#     except (FileNotFoundError, ValueError):
#         settingserror = True
#         logger.error("❌ Reload failed, keeping old config")

#     try:
#         make_folder_structure()
#     except PermissionError:
#         settingserror = True
#         logger.error("❌ Failure creating new folder structure")

#     if not settingserror:
#         logger.info("🙋 Loaded config successfully!")
#         grab_podcasts()  # No point grabbing podcasts adhoc if loading the config fails

#     upload_static()  # Ensure the static files are updated (inetaddress change)

#     logger.info("🙋 Finished adhoc config reload")


# if __name__ == "__main__":
#     signal.signal(signal.SIGHUP, reload_settings)

#     logger.info("🙋 Starting selfhostarchive.py strong, unphased.")
#     logger.info("🙋 Podcast Archive running! PID: %s", os.getpid())

#     settingsjson = get_settings(args)
#     make_folder_structure()

#     try:
#         main()
#     except KeyboardInterrupt:
#         print("\nExiting due to KeyboardInterrupt! 👋")
#         sys.exit(130)
