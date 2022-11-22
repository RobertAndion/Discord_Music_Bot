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