import json
import os
import os.path
from os import path


def _playlist_path(ctx) -> str:
    return os.path.join("Playlist", f"{ctx.author.id}.json")


def logUpdate(ctx, songName):
    user_file = os.path.join("SongLog", f"{ctx.author.id}.txt")
    with open(user_file, "a") as f:
        f.write(str(songName) + "\n")


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
    userpath = _playlist_path(ctx)
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
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return []


def list_playlists(ctx):
    userpath = _playlist_path(ctx)
    i = 1
    final = ""
    try:
        with open(userpath, "r") as file_read:
            data = json.load(file_read)
            for key in data:
                final += str(i) + ": " + key + "\n"
                i = i + 1

            return page_format(final)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def new_playlist(ctx, playlist_name, now_playing):
    userpath = _playlist_path(ctx)
    if path.exists(userpath):
        with open(userpath, "r") as read_file:
            data = json.load(read_file)
            data[playlist_name] = [now_playing]
            write_out(ctx, json.dumps(data, indent=1))
    else:
        dataStart = {playlist_name: [now_playing]}
        with open(userpath, "w") as write_file:
            json.dump(dataStart, write_file)


def write_out(ctx, data):
    userpath = _playlist_path(ctx)
    with open(userpath, "w") as f:
        f.write(data)


def delete_playlist(ctx, playlist_name):
    userpath = _playlist_path(ctx)
    if path.exists(userpath):
        try:
            with open(userpath, "r") as read_file:
                data = json.load(read_file)
            data.pop(playlist_name)
            write_out(ctx, json.dumps(data, indent=1))
            return "Done"
        except KeyError:
            return "Not-Found"
        except (json.JSONDecodeError, OSError):
            return "Not-Found"
    else:
        return "No-Playlists"


def delete_from_playlist(ctx, playlist_name, selection):
    userpath = _playlist_path(ctx)
    if path.exists(userpath):
        try:
            with open(userpath, "r") as read_file:
                data = json.load(read_file)
            data[playlist_name].pop(selection - 1)
            write_out(ctx, json.dumps(data, indent=1))
            return "Done"
        except (KeyError, IndexError, json.JSONDecodeError):
            return "Not-Found"
    else:
        return "No-Playlists"


def add_to_playlist(ctx, playlist_name, now_playing) -> bool:
    userpath = _playlist_path(ctx)
    if path.exists(userpath):
        try:
            with open(userpath, "r") as read_file:
                data = json.load(read_file)
            data[playlist_name].append(now_playing)
            write_out(ctx, json.dumps(data, indent=1))
            return True
        except (KeyError, json.JSONDecodeError, OSError):
            return False
    return False


def play_playlist(ctx, playlist_name):
    userpath = _playlist_path(ctx)
    if path.exists(userpath):
        with open(userpath, "r") as read_file:
            data = json.load(read_file)
            if playlist_name in data:
                return data[playlist_name]
            return False
    return False


def rename_playlist(ctx, raw_input) -> str:
    userpath = _playlist_path(ctx)
    parts = [s.strip() for s in raw_input.split(',')]
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return "Invalid-Input"
    try:
        with open(userpath, "r") as f:
            data = json.load(f)
        specific = data.pop(parts[0])
        data[parts[1]] = specific
        write_out(ctx, json.dumps(data, indent=1))
        return "Success"
    except FileNotFoundError:
        return "No-List"
    except (KeyError, json.JSONDecodeError):
        return "No-List"


def read_config():
    configPath = os.path.join("Resources", "config.json")
    try:
        with open(configPath, "r") as fileRead:
            data = json.load(fileRead)
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        raise Exception("Config file not found or malformed!")
