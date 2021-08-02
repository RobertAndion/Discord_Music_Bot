FROM ubuntu
RUN apt-get -y update && \
    apt-get install python3 -y && \
    apt-get install python3-pip -y && \
    apt-get install tmux -y && \
    apt-get install openjdk-13-jre-headless -y && \
    apt-get install cron -y && \
    apt-get install nano -y

RUN pip3 install --upgrade pip && \
    pip3 install discord.py lavalink python-dotenv psutil

ADD ./Bot /MusicBot
