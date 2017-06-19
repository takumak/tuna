#!/bin/bash

set -xe

rm -rf venv build dist Tuna.app Tuna.app.zip
$(dirname $(readlink -e $0))/../../tools/make_virtualenv.bash

(
  set -xe
  cd venv
  source bin/activate
  pip install pyinstaller

  cd tuna/dist/mac
  pyinstaller tuna.spec

  deactivate
)

mv dist/Tuna.app .
zip -r Tuna.app.zip Tuna.app
rm -rf venv build dist
