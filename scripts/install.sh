#!/usr/bin/env bash

# apt-get
if command -v apt-get &> /dev/null ; then
  sudo apt-get install -y $@
else
  echo "UNKNOWN PACKAGE MANAGER"
  exit 1
fi
