#!/bin/bash

SCRIPT_DIR=$(dirname "$0")

export LD_LIBRARY_PATH=:/usr/local/cuda/lib64:/usr/local/lib

export PYTHONIOENCODING=utf-8

. $SCRIPT_DIR/env01/bin/activate

(cd $SCRIPT_DIR
  nohup python ./sherpa_server.py >> sherpa_server.log 2>&1  &
)
