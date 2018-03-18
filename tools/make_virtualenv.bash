#!/bin/bash

set -xe

ROOT=$(dirname $(dirname $(readlink -e $0)))

if which pyenv >/dev/null 2>&1; then
  if pyenv versions --bare | grep '^3\.5\.5$' >/dev/null 2>&1; then
    :
  else
    (cd $(pyenv root) && git pull)
    pyenv install 3.5.5
  fi
  pyenv local 3.5.5
fi
pip install virtualenv

rm -rf venv
virtualenv --no-site-packages venv
source venv/bin/activate
pip install $(cat $ROOT/depends.txt)
deactivate
