#!/bin/bash

set -xe

ROOT=$(dirname $(dirname $(readlink -e $0)))

source venv/bin/activate
python src/tuna.py
deactivate
