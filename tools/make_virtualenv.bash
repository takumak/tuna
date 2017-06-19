#!/bin/bash

set -xe

ROOT=$(dirname $(dirname $(readlink -e $0)))

pyenv local 3.5.3
pip install virtualenv

rm -rf venv
virtualenv --no-site-packages venv

(
  set -xe
  cd venv
  source bin/activate
  pip install pyqt5 pyqtgraph numpy scipy pyexcel{,-io,-xls,-odsr}
  deactivate
  ln -s $ROOT tuna
)
