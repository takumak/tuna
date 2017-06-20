#!/bin/bash

NUMPY=numpy-1.13.0+mkl-cp35-cp35m-win32.whl
SCIPY=scipy-0.19.0-cp35-cp35m-win32.whl

if test ! \( -f $NUMPY -a -f $SCIPY \); then
  cat <<EOF
Download '$NUMPY' and '$SCIPY' manually from
http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy
and place it into $(pwd)
EOF
  exit 1
fi

set -xe

WINETRICKS_URL=https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
test ! -f winetricks && curl -LO $WINETRICKS_URL
PYTHON_VER=3.5.3
PYTHON_NAME=python-$PYTHON_VER
PYTHON_ZIP=$PYTHON_NAME-embed-win32.zip
PYTHON_ZIP_URL=https://www.python.org/ftp/python/$PYTHON_VER/$PYTHON_ZIP
test ! -f $PYTHON_ZIP && curl -LO $PYTHON_ZIP_URL

export WINEPREFIX=$(pwd)/wine
export WINEARCH=win32
rm -rf $WINEPREFIX

bash winetricks -q win10 vcrun2015
wine reg add 'HKCU\Software\Wine\DllOverrides' /v mscoree /t REG_SZ /d '' /f

cp $NUMPY $SCIPY wine/drive_c

(
  set -xe
  cd wine/drive_c
  (
    mkdir -p $PYTHON_NAME/Include
    touch $PYTHON_NAME/Include/pyconfig.h
    cd $PYTHON_NAME
    unzip ../../../$PYTHON_ZIP
    mv python35{,.a}.zip
    mkdir python35.zip
    (
      set -xe
      cd python35.zip
      unzip ../python35.a.zip
    )
  )
  git clone https://github.com/pypa/get-pip.git
  wine $PYTHON_NAME/python.exe get-pip/get-pip.py
  wine $PYTHON_NAME/python.exe -m pip install pyqt5 pyqtgraph \
       $NUMPY $SCIPY pyexcel{,-io,-xls,-odsr} pyinstaller
)

rm -rf build dist
wine wine/drive_c/$PYTHON_NAME/Scripts/pyinstaller.exe ../tuna.spec
mv dist/Tuna.exe .
rm -rf build dist wine
