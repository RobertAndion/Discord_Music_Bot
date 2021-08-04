#!/bin/bash
sleep 30
docker container start musicbot
sleep 5
docker exec -d --user=root musicbot tmux new-session -d 'cd /MusicBot/ && sh startup.sh'
