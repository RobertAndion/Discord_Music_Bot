Discord Music Bot created by Robert Andion USF Computer Science.

You must place all of the files in the same directory in order for this to work.
.setup will send you a message on how to configure the bot as long as you are the server admin.

If you want to change the lavalink password you must change it in the application.yml
and in both music.py and playlist.py on the commented lines where 'changeme123' is located.

You must also place your discord bot token in the .env file where prompeted.

Dependancies:
You must have java 11 for lavalink.
You must install python-dotenv, discord.py and lavalink.py links are listed below.
https://pypi.org/project/python-dotenv/
https://pypi.org/project/discord.py/
https://github.com/Devoxin/Lavalink.py

#######################################
Lava link is not my creation and can be found at:
lavalink.jar MUST BE DOWNLOADED AND PLACED IN DIRECTORY
https://github.com/Frederikam/Lavalink/releases

#######################################
run the lavalink server using the command : java -jar lavalink.jar
Then run the bot in a separate terminal using: python bot.py
Both terminals must remain running for the bot to be live, consider using tmux.

######################################
ALSO: Before many commands will work an initial "play" command will need to be made. Once this is done once
it will not need to be redone for the entirety of the bots run time. 

######################################
SETUP:
In order for music commands you must make a "Dj", "Administrator" or "DJ" role
and assign it to those you want to be able to play songs. 
(Future releases will have variable role names you can set in the code)

Admin functions will either need kick ban permissions for some commands or an "Admin" or "Administrator"
role. Everything is essentially role based to keep unwanted users from flooding the bot.

#################################################
COMMAND DOCUMENTATION:
NOTE: Anything in <> is an argument required by the function. Anything in () are alternate command shortcuts/names-------

.setup --------------------------
This command, if you are a server admin, will send you a private message with a short summary of how to use the bot.
It has no other function,

.play <SONG NAME> ------------------------
If the person using the command is in a voice channel and the bot has access to that channel it will connect and play the song listed.
This is also the command to continue adding songs to the queue, it covers both functions. The bot will auto disconnect
when the end of the queue is reached.

.skip ----------------------
If the bot is playing a song it will skip to the next song as long as the person is in the same
voice channel as the bot. If there are no songs after the bot will automatically disconnect.

.clear -------------------
This will clear all songs including now playing and the queue. This is the best way to disconnect the bot,
because it flushes everything first. Disconnect is still a command but will be removed in the future.

.stop -----------------
This is still in the code however it is commented out. It is an early method to stop the bot and pause
or clear is much better, this will be removed completely in the future.

.disconnect (dc) --------------
This command will disconnect the bot, however it is bad practice in most cases.
It will not stop the playing of songs or clear the queue. clear is the preferred command.

.pause (ps) -----------------
This command is a useful one to pause the bot. In current code it will never unpause 
on its own, you must upause or clear. I plan to upgrade this in future releases.

.unpause (resume,start,up) -------------
This will unpause a currently paused bot. (Should come after a pause command)

.queue (playlist,songlist,upnext) ------------
This will list all songs to be played next (one continuous list) with the currently playing
song at the top labeld as NP: this has replaced the now playing function however it is 
still commented out in the code to be removed in future releases.

.shuffle --------------------
This will shuffle the songs, although it will not show up this way on a queue command.
The order remains the same but the song picked is random. Good in tandem with the playlists,
it will continue to shuffle forever untill you do stopshuffle. (unshuffled by default) there may be an 
issue where if a last song is chosen during a shuffle it will end instead of playing more songs afterwards. 
(untested, this is a newer command)

.stopshuffle <unshuffle> ---------------
This will stop the shuffle command and return the function to the default state of unshuffled.
Also a newer lesser tested function with no known issues.

PLAYLIST COMMANDS:
NOTE: All playlists are stored by the persons name .json, in the future this will probably be changed to discord ID,
also all servers will be stored in the same folder, in the future server ID specific folders will likely be added. Also all 
commands are "currently playing" based. Keep this in mind when working with playlists.
 
.viewplaylist <Playlist name, case sensitive.> (vpl) ----------------
This will list the specific songs contained inside the specified playlist.
Nothing needs to be playing to use this command.

.listplaylists (lpl) --------------
This will list all of the users playlists whether or not the user is in a voice channel.

.deleteplaylist <Playlist name> (dpl) -------------
This will delete the entire playlist given with no confirmation and no reclamation.
Be certain before you delete as it is permanant.

.deletefromplaylist <Song number (maps with lpl command numbering), Playlistname> ---------
This function takes two paramaters, seperated by spaces. The first is the song number and
the second is the name of the playlist to delete the song from.

.createplaylist <Playlist name> (cpl) ---------------
This function will create a playlist of the given name. The first song will be the song currently playing
from the bot. If nothing is playing the command will fail not work.

.addtoplaylist <Playlist name> (atp) ---------------
Adds the currently playing song to the given playlist. Case sensitive.
If the playlist does not exist or no song is playing this will fail not work.

.playfromlist <Playlist name> (playl) ------------
This will play the entire playlist name given. Case sensitive. It will take some time to load all songs,
it will print a message when it is completely done.

All the functions in fileRead are used by commands and require no command to use. 

ADMIN COMMANDS:
NOTE: These require either "Administrator" or "Admin" commands for more advanced commands while intuitive
ones like ban and kick only require those permissions.

.kick <@membername> (boot) ------------
This will kick the named user out of the server.
It requires the ban and kick permissions.

.ban <@membername> (block) -----------
This will ban the named user from the server.
It requires the ban and kick permissions.

.assign Will finish the rest soon.

-- MORE COMMANDS -- TO BE LISTED.

Robert A -USF Computer Science
Todo:
Add a timer to the pause command.
Look into shuffle function.
