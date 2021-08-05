# Discord Music Bot 
### Created by Robert USF Computer Science.

This is a personal project of mine to create an easy to use and reliable discord music bot.
I hope you can find use in it as well!
Check out our other project written in Node.js: https://github.com/RobertAndion/DiscordMusicBotNode

### To Join our discord: 
https://discord.gg/YMaEKabS4m

## General Setup

### Dependancies:

You **must** have java 11 (or java 13) for lavalink.
The bot is written in and requires Python3
You must install python-dotenv, discord.py, lavalink.py and psutil, links are listed below.
* https://pypi.org/project/python-dotenv/
* https://pypi.org/project/discord.py/
* https://github.com/Devoxin/Lavalink.py
* https://pypi.org/project/psutil/

(psutil does not need to be installed if cpu functions are not needed, see more below.)

Lava link is not my creation and can be found at:
https://github.com/Frederikam/Lavalink/releases
(It can also be found in other Git branches. Any should be fine)
The lavalink.jar, 
**MUST BE DOWNLOADED AND PLACED IN DIRECTORY**

Keep the same file structure as the github repo for this to work, place Lavalink.jar at the "root" of the project.
Also, .setup will send a message on how to configure the bot as long as you are the server admin.

If you want to change the lavalink password you must change it in the application.yml
and in both music.py and playlist.py on the commented lines where 'changeme123' is located.

**Important:** You must also place your discord bot token in the .env file where prompted.

### Docker
If you wish to run the bot in a docker container the Docker folder provides a
dockerfile to do so. In order to use the file place the github files in a folder named Bot,
then place the dockerfile on the same level as the Bot folder (not inside) then run a normal build 
command. First set the correct .env and Playlist folder (if you have existing playlists) and they
will automatically be brought into the container. 

Docker start command:
```
docker run -it -m 2G --cpuset-cpus 0-1 --security-opt=no-new-privileges <image_id_here>
```
In this command the -m and --cpuset-cpus are optional but means that the container can use at most
two gigabytes of RAM and cpuset 0-1 means that the container can use threads 0 and 1. (Limiting resources)
All of this can be adjusted to suit or removed entirely. Keep --security-opt=no-new-privileges for security.

After this you can exit the container and rename it using
```
docker container ls -a
```
and then use the container id in the following command:
```
docker rename <container_id_here> musicbot
```
Now the automatic start file will boot up the container and automatically run the bot inside,
if the instructions below are followed.

#### Note:
You will be unable to update these containers from the inside so the command .backupPlaylists is here
in order to send you the playlists (only new info in the container) so you can remake the container images
often to get updates and changes to the bots code, simply place the .json lists back in the playlist folder
before building the new image and they will be added to the new image.

#### Automatic Docker Startup
In order to auto start, create the docker container and name it "musicbot",
then place the musicbotstart.sh on the containers host machine. In the host machine run the command:
(use sudo -i first if you need sudo to run docker, you should.)
```
crontab -e
```
Then choose nano if you are unfamiliar with linux editors, or pick your favorite editor. Add the following line to the bottom of
the file it opens
```
@reboot sh /pathtoyourfile/musicbotstart.sh
```
Now upon the main server restarting it will start up the docker container and run the bot inside.

## Full installation instructions:
### How to install packages

First ensure that you have python3 installed on your system, to do so enter python3 into a terminal
and you should be greeted by the python command line interface, to exit type quit()
Now that you have made sure you have python3 install pip.

##### Ubuntu:
```
sudo apt-get install python3-pip
```

##### Arch:
```
sudo pacman -S python-pip
```

Now that you have pip installed you can reference the links above on how to install each package with pip commands.
For example to install lavalink it is as simple as:
```
pip3 install lavalink
```
(Some will only need pip while other OS will need pip3 to be specified.)

The sections below will cover starting the bot with the Reboot command enabled or running it without.
I personally use Reboot often as many of the issues you may run across only need a quick reboot to get working again.

### Reboot command configuration
In order to use the new Reboot command you need to run the bot using tmux.
Installing tmux is simple

##### Ubuntu:
```
sudo apt-get install tmux
```

##### Arch:
```
sudo pacman -S tmux
```

### Running the bot with reboot capabilities:

In order to start the bot run
```
sh startup.sh
```
This will set up tmux with the proper session names in order to use the scripts provided.
This is a helpful new feature thats saves the time of having to log into the bot and reboot it manually.
Many issues are quickly solved with a reboot.


### Running the bot without reboot command capabilities:
run the lavalink server using the command: 
```
java -jar lavalink.jar
```
Then run the bot in a separate terminal using: 
```
python3 bot.py
```
Both terminals must remain running for the bot to be live, consider using tmux.

### Note:

Before many commands will work, an initial "play" command will need to be made. Once this is done once
it will not need to be redone for the entirety of the bots run time. This is not something to be fixed.
The player object doesn't exist until at least one play related command has been issued in a session.
Most commands have error handling for this now, run a play or playl command before trying to pause or 
unpause etc. (makes logical sense anyways.)


## Preparing to use the bot:
In order for music commands you must make a "Dj", "Administrator" or "DJ" role in discord
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
This command is tied to the owners discord ID so only the server owner may reboot. 
Please read more about how to set it up above.
Note: This function should be used before trying clearcache to fix bot errors.
*To not use this function remove line 4, and 40-44 in bot.py*

```
.backupPlaylists
```
This command will only work for the bot owner and will private message them a zip file of all playlists.
This is especially useful for Docker containers where the only thing you would need out before making a new 
version are the playlists.

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
Removed completely now, will be removed on next readme update/release.

```
.disconnect (dc) 
```
This command will disconnect the bot, however it is bad practice in most cases.
It will not stop the playing of songs or clear the queue. clear is the preferred command.
This has now been removed. It is still present in the code but commented out.
**Not recomended**

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

```
.shuffle
```
This no longer uses the given shuffle function from lavalink.
It is a custom function that shuffles in a finalized form,
viewable in the queue command.


```
.clearbotcache
```
**Currently removed** So far I have not needed this with the new API so it has been removed.(Dangerous anyways)
**Warning** This is to be used as a last resort ONLY. Better to reboot the bot.
This will clear the player cache from your server. Do not do this for minor issues, try restarting the bot (and/or Lavalink) first,
or kicking it and reinviting it. This command can currupt data, the bot **MUST** be disconnected before using this.
Furthermore for the safety of this command it is restricted to those with administrator permissions only.

## PLAYLIST COMMANDS:
### NOTE: 
All playlists are stored by the discord ID with file extension .json, also all servers will be stored in the same folder, 
in the future server ID specific folders will likely be added. Also all 
commands are "currently playing" based. Keep this in mind when working with playlists.

```
.viewplaylist <Playlist name (case sensitive), OPTIONAL page number> (vpl)
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

## CPU Commands:
### NOTE: cpu.py is a new option and will require extra work to get working.
##### If this functionality is undesired you can remove line 34 from bot.py and delete cpu.py. You will also not need the psutil package

```
.cpu_info <> (cpu)
```
This will show current cpu information such as % usage, load and temperature.
The temperature will take some adjustment to get working. First change line 29 in cpu.py to:
```
embed.description += str(psutil.sensors_temperatures(fahrenheit=False)) + " C \n"
```
This will print a full JSON package of the available sensors then select the proper one as I did for one server in the actual code.

```
.server_info <> (serverinfo)
```
This provides more permanant information such as thread count, RAM, and currently available RAM.
(Should be cross system compatible.)


Robert A -USF Computer Science

Todo/Possible adds in the future:
Add the option to customize the message and role given through discord commands. Future update coming.
Add a delete from queue function that removes a specific song from the queue based on position.
Update: The custom function for shuffling has been done.
