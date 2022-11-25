import json
import os.path
from os import path


def logUpdate(ctx, songName):
    user_file = os.path.join("SongLog", str(ctx.author.id))
    user_file = str(user_file) + ".txt"
    user_write = open(user_file, "a")
    user_write.write(str(songName) + "\n")
    user_write.close()


def page_format(raw_input) -> list:
    list_collection = []
    i = 0
    temp = ''
    for song in raw_input.splitlines():
        temp = temp + '\n' + song
        i = i + 1
        if i % 10 == 0:
            list_collection.append(temp)
            temp = ''

    if i % 10 != 0:
        list_collection.append(temp)
    return list_collection


def playlist_read(listname, ctx):
    userpath = os.path.join("Playlist", str(ctx.author.id))
    userpath = str(userpath) + ".json"
    i = 1
    try:
        with open(userpath, "r") as fileRead:
            data = json.load(fileRead)
            specific = data[listname]
            final = ""
            for item in specific:
                final += str(i) + ": " + item + "\n"
                i = i + 1
            return page_format(final)
    except:
        return []


def list_playlists(ctx):
    userpath = os.path.join("Playlist", str(ctx.author.id))
    userpath = str(userpath) + ".json"
    i = 1
    final = ""
    try:
        with open(userpath, "r") as file_read:
            data = json.load(file_read)
            for key in data:
                final += str(i) + ": " + key + "\n"
                i = i + 1

            return page_format(final)
    except:
        return []

# function to create a new playlist in the JSON file or make a JSON file if none exists for the user


def new_playlist(ctx, playlist_name, now_playing):
    userpath = os.path.join("Playlist", str(ctx.author.id))
    userpath = str(userpath) + ".json"
    if path.exists(userpath):
        with open(userpath, "r") as read_file:
            data = json.load(read_file)
            temp = [now_playing]
            data[playlist_name] = temp
            dataFinal = json.dumps(data, indent=1)
            write_out(ctx, dataFinal)
    else:
        dataStart = {playlist_name: [now_playing]}
        with open(userpath, "w") as write_file:
            json.dump(dataStart, write_file)


def write_out(ctx, data):
    userpath = os.path.join("Playlist", str(ctx.author.id))
    userpath = str(userpath) + ".json"
    file = open(userpath, "w")
    file.write(data)
    file.close()


def delete_playlist(ctx, playlist_name):
    userpath = os.path.join("Playlist", str(ctx.author.id))
    userpath = str(userpath) + ".json"
    if path.exists(userpath):
        with open(userpath, "r") as read_file:
            data = json.load(read_file)
            try:
                data.pop(playlist_name)
                dataFinal = json.dumps(data, indent=1)
                write_out(ctx, dataFinal)
                return "Done"
            except:
                return "Not-Found"
    else:
        return "No-Playlists"


def delete_from_playlist(ctx, playlist_name, selection):
    userpath = os.path.join("Playlist", str(ctx.author.id))
    userpath = str(userpath) + ".json"
    if path.exists(userpath):
        with open(userpath, "r") as read_file:
            try:
                data = json.load(read_file)
                data[playlist_name].pop(selection - 1)
                dataFinal = json.dumps(data, indent=1)
                write_out(ctx, dataFinal)
                return "Done"
            except:
                return "Not-Found"

    else:
        return "No-Playlists"

# Reads json, finds playlists and add song then uses help_newplaylist to write back.


def add_to_playlist(ctx, playlist_name, now_playing) -> bool:
    userpath = os.path.join("Playlist", str(ctx.author.id))
    userpath = str(userpath) + ".json"
    if path.exists(userpath):
        try:
            with open(userpath, "r") as read_file:
                data = json.load(read_file)
                temp = [now_playing]
                data[playlist_name] += temp
                dataFinal = json.dumps(data, indent=1)
                write_out(ctx, dataFinal)
                return True

        except:
            return False

# loads songs from a playlist to be parsed by the calling function


def play_playlist(ctx, playlist_name):
    userpath = os.path.join("Playlist", str(ctx.author.id))
    userpath = str(userpath) + ".json"
    if path.exists(userpath):
        # using with auto closes the file after.
        with open(userpath, "r") as read_file:
            data = json.load(read_file)
            if playlist_name in data:
                songlist = data[playlist_name]
                return songlist
            else:
                # return false if playlist doesnt exist which will be caught by music.py and output playlist doesnt exist.
                return False
    else:
        return False  # same as above comment


def rename_playlist(ctx, raw_input) -> bool:
    userpath = os.path.join("Playlist", str(ctx.author.id))
    userpath = str(userpath) + ".json"
    splitNames = raw_input.split(',')
    try:
        if splitNames[0] is not None and splitNames[1] is not None:
            data = ""
            specific = ""
            try:
                with open(userpath, "r") as fileRead:
                    data = json.load(fileRead)
                    specific = data[splitNames[0].strip()]
                with open(userpath, "w") as fileRead:
                    data.pop(splitNames[0].strip())  # pop off old playlist
                    # store the same data as a new list.
                    data[splitNames[1].strip()] = specific
                    dataFinal = json.dumps(data, indent=1)
                    write_out(ctx, dataFinal)
                    return "Success"
            except:
                return "No-List"
    except:
        return "Invalid-Input"


def read_config():
    configPath = os.path.join("Resources", "config.json")
    try:
        with open(configPath, "r") as fileRead:
            data = json.load(fileRead)
            return data
    except:
        raise Exception("Config file not found!")
