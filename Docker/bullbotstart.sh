#!/bin/bash
docker container start musicbot
sleep 5
docker exec -d musicbot tmux new-session -d 'cd /MusicBot/ && sh startup.sh'
