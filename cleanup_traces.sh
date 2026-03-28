#!/bin/bash
echo ">>> Sweeping gem5 m5out directories..."
rm -f /home/yuvalk/spec2017/benchspec/CPU/*/data/refrate/input/m5out/*.txt
rm -rf /home/yuvalk/MBMM/m5out/*
echo "SUCCESS: Raw traces deleted. Disk space reclaimed."