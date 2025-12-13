#!/bin/bash
# Install Aurora AI Kernel Extensions
cd /opt/aurora/kernel_extensions
make clean && make
make install
depmod -a
echo "Aurora AI Kernel Extensions installed successfully"
