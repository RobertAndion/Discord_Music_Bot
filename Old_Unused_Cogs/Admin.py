from discord.ext import commands
import discord
from discord.utils import get

class Admin(commands.Cog):
    def __init__(self,bot):
        self.bot = bot


    @commands.command(name = 'kick', aliases = ['boot'],description="Used by admins to kick members") #working kick command
    @commands.has_permissions(ban_members=True, kick_members=True)
    async def kick_user(self,ctx, member : discord.Member, *, reason =None):
        await member.kick(reason=reason)
        await ctx.channel.send(member.display_name + " was kicked.")


    @commands.command(name = 'ban', aliases = ['block'],description="Used by admins to ban members") #Working ban command
    @commands.has_permissions(ban_members=True, kick_members=True)
    async def ban_user(self,ctx,member : discord.Member, *, reason=None):
        await member.ban(reason=reason)
        await ctx.channel.send(member.display_name + " has been banned from the server.")


    @commands.command(name='assign', description="Usable by Admins to assign roles to server members.") #command to assign roles to users
    @commands.has_any_role('Administrator','Admin')
    async def assign_role(self,ctx,member : discord.Member, *, role_name):
        role = get(ctx.guild.roles,name = role_name)
       # member : Member = get(ctx.guild.members,name = user_name)
        await member.add_roles(role)
        await ctx.channel.send(str(role) + " was successfully given to " + str(member.display_name))


    @commands.command(name="log",description="Shows log for specific user. Provide name and number of entries to display")
    @commands.has_any_role("Administrator","Admin")
    async def get_log(self,ctx,member : discord.Member, limiter : int):
        logs = await ctx.guild.audit_logs(limit = limiter, user = member).flatten()
        for log in logs:
            await ctx.channel.send('Peformed {0.action} on {0.target}'.format(log))

        await ctx.channel.send("All logs requested have been shown.")
      #  async for entry in ctx.guild.audit_logs(limit=15):
       # two lines for all users     await ctx.channel.send('{0.user} performed {0.action} on {0.target}'.format(entry))
        

    @commands.command(name="move")
    @commands.has_any_role("Administrator","Admin")
    async def move_voice(self,ctx,member : discord.Member, new_channel_raw):
        if member.voice is not None:
            new_channel = get(member.guild.channels, name = new_channel_raw)
            await member.move_to(new_channel)
            await ctx.author.send("Moved user")
        else:
            await ctx.author.send("Couldnt move user, not connected to voice chat.")


    @commands.command(name="disconnectuser",aliases=['dcuser'])
    @commands.has_any_role("Administrator","Admin")
    async def disconnect_user(self,ctx, member: discord.Member):
        if member.voice is not None:
            await member.move_to(None)
            await ctx.author.send("User disconnected.")
        else:
            await ctx.author.send("Cannot disconnect user, they are not connected to voice chat.")

# This catches errors but causes one when shutting down a bot.
    @commands.Cog.listener() #event listener for error handling
    async def on_command_error(self, ctx, error):
        if ctx.command is not None:
            print(ctx.command.name + " was used incorrectly")
            print(error)

        else:
            print("Command does not exist.")


async def setup(bot):
    await bot.add_cog(Admin(bot))