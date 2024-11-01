#!/bin/bash

python3 calculator.py
if [ $? -ne 0 ]; then
    echo "运行计算器失败"
    exit 1
fi