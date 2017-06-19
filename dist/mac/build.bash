#!/bin/bash

set -xe

env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install -s 3.5.3
pyenv local 3.5.3
python -m pip install virtualenv

rm -rf venv build dist Tuna.app Tuna.app.zip
python -m virtualenv --no-site-packages venv

(
  set -xe
  cd venv
  source bin/activate
  pip install pyqt5 pyqtgraph numpy scipy pyexcel{,-io,-xls,-odsr} pyinstaller

  ln -s ../../../../tuna
  cd tuna/dist/mac
  pyinstaller tuna.spec

  deactivate
)

mv dist/Tuna.app .
zip -r Tuna.app.zip Tuna.app
rm -rf venv build dist
