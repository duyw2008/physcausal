#!/bin/bash
cd /home/duyw/physcausal
exec python3 -u run_evo.py >> data/evo_output.log 2>&1
