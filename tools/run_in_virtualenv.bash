#!/bin/bash

set -xe

ROOT=$(dirname $(dirname $(readlink -e $0)))

(
  set -xe
  cd venv
  source bin/activate
  python tuna/src/tuna.py
  deactivate
)
