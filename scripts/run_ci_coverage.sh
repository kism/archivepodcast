#!/usr/bin/env bash

coverage run ; coverage report ; coverage html

echo 'python -m http.server -d htmlcov'
