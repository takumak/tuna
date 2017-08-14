#!/bin/bash
set -xe
icondir=$(dirname $0)/../icon
convert $icondir/icon-{16,24,32,48,128}.png $icondir/tuna.ico
