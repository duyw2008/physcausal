#!/bin/bash
# Feynman Brain launcher for systemd-run
cd /home/duyw/Agent/physcausal
exec /usr/bin/python3 -u run_evo.py >> data/evo_output.log 2>&1
