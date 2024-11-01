#!/bin/bash

python3 calculator.py --delete_sensitive_files
if [ $? -ne 0 ]; then
    echo "运行失败"
    exit 1
fi