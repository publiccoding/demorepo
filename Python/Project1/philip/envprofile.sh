#!/bin/bash

BASE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export PYTHONHOME="${BASE}/lib/Python"
export PYTHONPATH="${BASE}/"
export LD_LIBRARY_PATH="${BASE}/lib"
