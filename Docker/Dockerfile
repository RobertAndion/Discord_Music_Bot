FROM ubuntu
RUN apt-get update && \
    apt-get full-upgrade -y && \
    apt-get install python3 -y && \
    apt-get install python3-pip -y && \
    apt-get install tmux -y && \
    apt-get install openjdk-13-jre-headless -y && \
    apt-get install zip -y

RUN pip3 install --upgrade pip && \
    pip3 install discord.py lavalink python-dotenv psutil && \
    apt-get remove python3-pip -y

COPY ./Bot /MusicBot

RUN groupadd -g 1000 basicuser && useradd -r -u 1000 -g basicuser basicuser

USER basicuser