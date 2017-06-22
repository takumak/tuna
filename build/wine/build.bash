#!/bin/bash

set -xe

ROOT=$(dirname $(realpath $0))/../..
SPEC=$ROOT/build/tuna.spec
OUTDIR=$ROOT/dist

NUMPY=numpy-1.13.0+mkl-cp35-cp35m-win_amd64.whl
SCIPY=scipy-0.19.1-cp35-cp35m-win_amd64.whl

if test ! \( -f $NUMPY -a -f $SCIPY \); then
  cat<<EOF
Download following 2 files:
  * $NUMPY
  * $SCIPY
from:
  http://www.lfd.uci.edu/~gohlke/pythonlibs/
and place these files into:
  $(pwd)
EOF
  exit 1
fi


export WINEPREFIX=$(pwd)/wine
rm -rf $WINEPREFIX python-msi build dist


WINETRICKS_URL=https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
test ! -f winetricks && curl -LO $WINETRICKS_URL
bash winetricks win8


PYTHON_EXE_URL=https://www.python.org/ftp/python/3.5.3/python-3.5.3-amd64-webinstall.exe
PYTHON_EXE=${PYTHON_EXE_URL##*/}
test ! -f $PYTHON_EXE && curl -LO $PYTHON_EXE_URL


wine $PYTHON_EXE /quiet /layout python-msi
for n in core dev exe lib tools pip; do
  wine msiexec /i python-msi/$n.msi targetdir='c:\python'
done

PYTHON=wine/drive_c/python/python.exe
wine $PYTHON -m ensurepip
wine $PYTHON -m pip install $NUMPY
wine $PYTHON -m pip install $SCIPY
wine $PYTHON -m pip install \
    pyqt5 pyqtgraph \
    pyexcel pyexcel-io pyexcel-xls pyexcel-odsr \
    pyinstaller

wine wine/drive_c/python/Scripts/pyinstaller.exe $SPEC
mkdir -p $OUTDIR
cp dist/Tuna.exe $OUTDIR
