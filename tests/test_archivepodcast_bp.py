"""Tests the blueprint's HTTP endpoint."""

import logging
from http import HTTPStatus

from flask.testing import FlaskClient

from archivepodcast import create_app


