#!/bin/bash

set -xe

WINETRICKS_URL=https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
test ! -f $WINETRICKS_URL && curl -LO $WINETRICKS_URL
test ! -d get-pip && git clone https://github.com/pypa/get-pip.git
PYTHON_VER=3.5.3
PYTHON_NAME=python-$PYTHON_VER
PYTHON_ZIP=$PYTHON_NAME-embed-win32.zip
PYTHON_ZIP_URL=https://www.python.org/ftp/python/$PYTHON_VER/$PYTHON_ZIP
test ! -f $PYTHON_ZIP && curl -LO $PYTHON_ZIP_URL

export WINEPREFIX=$(pwd)/wine
export WINEARCH=win32
rm -rf $WINEPREFIX
bash winetricks vcrun2015

(
  set -xe
  mkdir wine/drive_c/$PYTHON_NAME
  cd wine/drive_c/$PYTHON_NAME
  unzip ../../../$PYTHON_ZIP
  mv python35{,.a}.zip
  mkdir python35.zip
  (
    set -xe
    cd python35.zip
    unzip ../python35.a.zip
  )
  wine python.exe ../../../get-pip/get-pip.py
)
