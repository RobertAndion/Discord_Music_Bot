#!/bin/bash
tmux new-session -d 'sh kill.sh && sleep 5 && sh startup.sh'