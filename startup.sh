#!/bin/bash
tmux new-session -s Lavalink -d 'java -jar Lavalink.jar'
sleep 20
tmux new-session -s Bot -d 'python3 ./bot.py'
