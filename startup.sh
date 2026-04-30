#!/bin/bash
java -jar Lavalink.jar &
sleep 20
exec python3 bot.py
