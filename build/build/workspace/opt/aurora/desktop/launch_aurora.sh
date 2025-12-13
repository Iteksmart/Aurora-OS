#!/bin/bash
# Launch Aurora Desktop Environment
export PYTHONPATH=/opt/aurora:$PYTHONPATH
cd /opt/aurora/desktop
python3 compositor.py
