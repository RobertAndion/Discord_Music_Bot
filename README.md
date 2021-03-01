# Discord Music Bot 
### Created by Robert USF Computer Science.

This is a personal project of mine to create an easy to use and reliable discord music bot.
I hope you can find use in it as well!

You must place all of the files in the same directory in order for this to work.
.setup will send you a message on how to configure the bot as long as you are the server admin.

If you want to change the lavalink password you must change it in the application.yml
and in both music.py and playlist.py on the commented lines where 'changeme123' is located.

Important: You must also place your discord bot token in the .env file where prompted.

### Dependancies:
You must have java 11 (or java 13) for lavalink.
You must install python-dotenv, discord.py and lavalink.py links are listed below.
https://pypi.org/project/python-dotenv/
https://pypi.org/project/discord.py/
https://github.com/Devoxin/Lavalink.py

### Optional
In order to use the new Reboot command you need to run the bot using tmux.
Installing tmux is simple

#### Debian:
```
sudo apt-get install tmux
```

#### Arch:
```
sudo pacman -S tmux
```

### Startup:

In order to start the bot run
```
sh startup.sh
```
This will set up tmux with the proper session names in order to use the scripts provided.
This is a helpful new feature thats saves the time of having to log into the bot and reboot it manually.
Many issues are quickly solved with a reboot.

Lava link is not my creation and can be found at:
lavalink.jar **MUST BE DOWNLOADED AND PLACED IN DIRECTORY**
https://github.com/Frederikam/Lavalink/releases

### Running the bot (Without the reboot command compatibility):
run the lavalink server using the command: 
```
java -jar lavalink.jar
```
Then run the bot in a separate terminal using: python bot.py
Both terminals must remain running for the bot to be live, consider using tmux.

Before many commands will work an initial "play" command will need to be made. Once this is done once
it will not need to be redone for the entirety of the bots run time. (This may have been fixed)


## SETUP:
In order for music commands you must make a "Dj", "Administrator" or "DJ" role
and assign it to those you want to be able to play songs. 
(Future releases will have variable role names you can set in the code)

Admin functions will either need kick ban permissions for some commands or an "Admin" or "Administrator"
role. Everything is essentially role based to keep unwanted users from flooding the bot.

## COMMAND DOCUMENTATION:
### NOTE: 
Anything in <> is an argument required by the function. Anything in () are alternate command shortcuts/names
```
.setup
```
This command, if you are a server admin, will send you a private message with a short summary of how to use the bot.
It has no other function.

```
.reboot
```
This command will reboot both Lavalink and the bot directly from discord. 
Right now it requires administrator permissions but in the future it will be tied to the
owners discord ID so only the server owner may reboot. 
Please read more about how to set it up above.
*To not use this function remove line 4, and 40-44 in bot.py*

```
.play <SONG-NAME>
```
If the person using the command is in a voice channel and the bot has access to that channel it will connect and play the song listed.
This is also the command to continue adding songs to the queue, it covers both functions. The bot will auto disconnect
when the end of the queue is reached.

```
.skip <OPTIONAL amount>
```
If the bot is playing a song it will skip to the next song as long as the person is in the same
voice channel as the bot. If there are no songs after the bot will automatically disconnect. 
The argument can be used to say how many songs to skip.

```
.clear
```
This will clear all songs including now playing and the queue. This is the best way to disconnect the bot,
because it flushes everything first. Disconnect is still a command but will be removed in the future.

```
.stop
```
Removed completely now.

```
.disconnect (dc) 
```
This command will disconnect the bot, however it is bad practice in most cases.
It will not stop the playing of songs or clear the queue. clear is the preferred command.
**Not reccomended**

```
.pause (ps)
```
This command is a useful one to pause the bot. The command has now been update.
It will now unpause automatically after 7 minutes of being paused. This can be changed
manually under the pause command. change the sleep(number of seconds here) to any amount of time.
Other commands can still be used including unpause during this "wait" period.

```
.unpause (resume,start,up)
```
This will unpause a currently paused bot. (Should come after a pause command)
This will automatically happen after 7 minutes afte a pause command by default.

```
.queue <OPTIONAL page number> (playlist,songlist,upnext)
```
This will list all songs to be played next in pages of 10 with the currently playing
song at the top of page 1 labeled as NP. The current page and total pages are displayed 
at the bottom, like so, Page: 5/6 means you are on page 5 out of a total of 6 pages. 
No argument assumes page one, negative or 0 goes to page 1 and a page larger than the total
goes to the last page. 

**Updated**
```
.shuffle
```
This no longer uses the given shuffle function from lavalink.
It is a custom function that shuffles in a finalized form,
viewable in the queue command.

**Removed**
```
.stopshuffle (unshuffle)
```
This will stop the shuffle command and return the function to the default state of unshuffled.

```
.clearbotcache
```
This will clear the player cache from your server. Do not do this for minor issues, try restarting the bot (and/or Lavalink) first,
or kicking it and reinviting it. This command can currupt data, the bot MUST be disconnected before using this.
Furthermore for the safety of this command it is restricted to those with administrator permissions only.

## PLAYLIST COMMANDS:
### NOTE: 
All playlists are stored by the discord ID with file extension .json, also all servers will be stored in the same folder, 
in the future server ID specific folders will likely be added. Also all 
commands are "currently playing" based. Keep this in mind when working with playlists.

```
.viewplaylist <Playlist name, case sensitive., OPTIONAL page number> (vpl)
```
This will list the specific songs contained inside the specified playlist.
Nothing needs to be playing to use this command. If you have more than 20 songs in a playlist,
they will now send in pages of 20 to avoid "invisible" playlists if they are too big.
(No need to be in a voice channel to use this command)

```
.listplaylists <OPTIONAL page number> (lpl)
```
This will list all of the users playlists whether or not the user is in a voice channel.
The playlists will now show up in pages of 10, if you have more than 10 playlists
provide the page number you wish to go to after lpl (page total listed on the bottom
similar to the queue command.)

```
.deleteplaylist <Playlist name> (dpl)
```
This will delete the entire playlist given with no confirmation and no reclamation.
Be certain before you delete as it is permanant.

```
.deletefromplaylist <Song number (maps with vpl command numbering), Playlistname>
```
This function takes two paramaters, seperated by spaces. The first is the song number and
the second is the name of the playlist to delete the song from.

```
.createplaylist <Playlist name> (cpl)
```
This function will create a playlist of the given name. The first song will be the song currently playing
from the bot. If nothing is playing the command will fail not work.

```
.addtoplaylist <Playlist name> (atp)
```
Adds the currently playing song to the given playlist. Case sensitive.
If the playlist does not exist or no song is playing this will fail not work.

```
.playfromlist <Playlist name> (playl)
```
This will play the entire playlist name given. Case sensitive. It will take some time to load all songs,
it will print a message when it is completely done.

```
.renameplaylist <current name,new name> (rpl)
```
This function will rename an existing playlist. The names must be seperated by a comma
and no spaces before or after the comma. 

**NEW**
```
.addqueuetolist <Playlist name> (aqtp)
```
This function will add the entire queue to a given playlist.
It does not add the currently playing song, this way if you make a playlist just for the queue,
it will not add the currently playing song twice.

## ADMIN COMMANDS:
### NOTE: 
These require either "Administrator" or "Admin" commands for more advanced commands while intuitive
ones like ban and kick only require those permissions.

```
.kick <@membername> (boot)
```
This will kick the named user out of the server.
It requires the ban and kick permissions.

```
.ban <@membername> (block)
```
This will ban the named user from the server.
It requires the ban and kick permissions.

```
.assign <@membername, Role>
```
Used to assign a role to a user on text command. Once this is done that role will be locked to bot control.
The first argument is the @user and he second is the name of the roll. Requires "Admin" or "Administrator" role.

```
.log <@membername, amount>
```
Will list the actions performed by the person for x amount of entries. ex: .log @Rob 12 
will show the last 12 actions (If there are that many) for rob. Requires "Administrator" or "Admin" role.

```
.move <@member, channel name>
```
This will move the given user into the channel name listed. Requires the "Administrator" or "Admin" role.

```
.disconnectuser <@membername> (dcuser)
```
This will disconnect the named user from voice channels. Requires the "Administrator" or "Admin" role.

##### The Administration functions can be removed if undesired by deleting Admin.py from the directory and removing line 29 from bot.py 
##### 'client.load_extension('Admin')' This is the command that loads in the Cog.


## WELCOME FUNCTIONS:

In order to use the welcome functions you must enable "Privileged Gateway Intents" on the discord developer page under the Bot section. Enable the
"SERVER MEMBERS INTENT" this will allow the function to welcome new members.

These are automated functions that will activate on a new member joining. They will be greeted in your "general" chat
and given the role "Example" automatically. These should be changed to your unique needs, and the role should be created and customized in your server first.
If you do not want automatic roles the two lines to remove are marked in the welcome.py file. There are also comments there that 
direct you how to changed the channel the announcement will be placed in. There is also the option to change the printed message.

NOTE: The role will follow any server you add it to and fail. If you plan to have the bot in more than one server add the following instead
of the current two lines for the role.
```
if servername == "YourServerHere":
    role = get(member.guild.roles, name = serverrolename)   #Remove this line and below to not add a role to a new user  
    await member.add_roles(role)    #Remove me if you remove the line above.  
```

This will make it so the role function only applies to your server. You can put the greeting under this protection as well,
however most servers have a general chat. The name of the user and of the server are dynamicaly coded.

(**FUTURE:** In the future the if statement above will not be needed. Server specific files will be created and managed through the bot to control this.)

The welcome functions can be removed by deleting line 30 in bot.py and deleting welcome.py.
'client.load_extension('welcome')' This is the command that loads in the Cog.
You must also delete line 8 and 9 from bot.py to remove discord intents if you do not want to use welcome functions.

### All the functions in fileRead are used by commands and require no command to use (Helper functions). 


Robert A -USF Computer Science

Todo/Possible adds in the future:
Add the option to customize the message and role given through discord commands. Future update coming.

Update: The custom function for shuffling has been done.