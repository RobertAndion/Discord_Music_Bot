from discord.ext import commands
import discord
import json
from discord.utils import get
from discord import Embed
import os.path
from os import path
"""
Robert A. USF Computer Science
This function is a helper function to playlist.py to help with the process of reading in and writing out
to JSON.
"""

def logUpdate(member : discord.Member, songName): #automatically logs all songs played by a user in a textfile named their name.
    user_file = os.path.join("SongLog",member.display_name) 
    user_file = str(user_file) + ".txt"
    user_write = open(user_file,"a")
    user_write.write(str(songName) + "\n")


def playlist_read(listname,ctx):
    userpath = os.path.join("Playlist",ctx.author.display_name) 
    userpath = str(userpath) + ".json"
    i = 1
    try:
        with open(userpath,"r") as fileRead:
            data = json.load(fileRead)
            specific = data[listname]
            final = ""
            for item in specific:
                final += str(i) + ": " + item + "\n"
                i = i + 1
            return final
    except Exception as error:
        return "Failed-Process"
        print (error)


def list_playlist(ctx): #function to list all of the users playlists.
    userpath = os.path.join("Playlist",ctx.author.display_name) 
    userpath = str(userpath) + ".json"
    i = 1
    final = ""
    try:
        with open(userpath,"r") as file_read:
            data = json.load(file_read)
            for key in data:
                final+= str(i) + ": " + key + "\n"
                i = i + 1
            return final
    except Exception as error:
        return "Failed-Process"


def new_playlist(ctx,playlist_name,now_playing): #function to create a new playlist in the JSON file or make a JSON file if none exists for the user
    userpath = os.path.join("Playlist",ctx.author.display_name) 
    userpath = str(userpath) + ".json"
    if path.exists(userpath):
        with open(userpath,"r") as read_file:
            data = json.load(read_file)
            temp = [now_playing]
            data[playlist_name] = temp
            dataFinal = json.dumps(data, indent = 1)
            help_newplaylist(ctx,dataFinal)
    else: 
        dataStart = {playlist_name:[now_playing]}
        with open(userpath,"w") as write_file:
            json.dump(dataStart,write_file)


def help_newplaylist(ctx,data): #has no safety checks to write. needs to be done before hand only a helper function for within the doc
    userpath = os.path.join("Playlist",ctx.author.display_name) 
    userpath = str(userpath) + ".json"
    file = open(userpath,"w")
    file.write(data)
    #with open(userpath,"w") as write_file:
        #json.dump(data,write_file)

def delete_playlist(ctx,playlist_name):
    userpath = os.path.join("Playlist",ctx.author.display_name) 
    userpath = str(userpath) + ".json"
    if path.exists(userpath):
        with open(userpath,"r") as read_file:
            data = json.load(read_file)
            try:
                data.pop(playlist_name)
                dataFinal = json.dumps(data, indent = 1)
                help_newplaylist(ctx,dataFinal)
                return "Done"
            except Exception as error:
                return "Not-Found"
    else: 
        return "No-Playlists"


def delete_from_playlist(ctx, playlist_name,selection):
    userpath = os.path.join("Playlist",ctx.author.display_name) 
    userpath = str(userpath) + ".json"
    if path.exists(userpath):
        with open(userpath,"r") as read_file:
            try:
                data = json.load(read_file)
                data[playlist_name].pop(selection - 1)
                dataFinal = json.dumps(data, indent = 1)
                help_newplaylist(ctx,dataFinal)
                return "Done"
            except Exception as error:
                return "Not-Found"
                
    else: 
        return "No-Playlists"


def add_to_playlist(ctx,playlist_name,now_playing): # Reads json, finds playlists and add song then uses help_newplaylist to write back.
    userpath = os.path.join("Playlist",ctx.author.display_name) 
    userpath = str(userpath) + ".json"
    if path.exists(userpath):
        try:
            with open(userpath,"r") as read_file: #focusing on format here at first
                data = json.load(read_file) 
                temp = [now_playing]
                data[playlist_name] += temp
                dataFinal = json.dumps(data, indent = 1)
                help_newplaylist(ctx,dataFinal)
                return True

        except Exception as error:
            return False


def play_playlist(ctx,playlist_name): # loads songs from a playlist to be parsed by the calling function
    userpath = os.path.join("Playlist",ctx.author.display_name) 
    userpath = str(userpath) + ".json"
    if path.exists(userpath):
        with open(userpath,"r") as read_file:
            data = json.load(read_file)
            if playlist_name in data:
                songlist = data[playlist_name]
                return songlist
            else:
                return False #return false if playlist doesnt exist which will be caught by music.py and output playlist doesnt exist.
    else:
        return False #same as above comment