import os
import discord
from pymongo import MongoClient
from discord.ext import commands, tasks
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
USER = os.getenv('DB_USER')
PASS = os.getenv('DB_PASS')
CONNECTION_STR = f"mongodb+srv://{USER}:{PASS}@cluster0.pss26.gcp.mongodb.net/study_cafe?retryWrites=true&w=majority"

client_db = MongoClient(CONNECTION_STR)
db = client_db.study_cafe
collection_prefixes = db.prefixes
collection_goals = db.user_goals

embed_colour = 0xFF5733

now = datetime.now() # current date and time
formatted_time = now.strftime("%H:%M")

def get_prefix(client, message): #first we define get_prefix
    document = collection_prefixes.find_one({"_id": str(message.guild.id)}) #find the infomation of the server via guild id
    return str(document["prefix"])

# intents = discord.Intents(messages=True, guilds=True)
# intents.reactions = True
# intents.typing = False
# intents.presences = False
client = commands.Bot(command_prefix = (get_prefix),intents=discord.Intents.all(),) #TODO: intents will eventually have to be more specific if this bot gets widely used

@client.event
async def on_guild_join(guild): #when the bot joins the guild
    str_record = {"_id": str(guild.id), "prefix": "sc!"} #creating default prefix and parse into db
    collection_prefixes.insert_one(str_record)

@client.event
async def on_guild_remove(guild): #when the bot is removed from the guild
    collection_prefixes.delete_many({"_id": str(guild.id)}) #delete all data about the guild including the prefix
    collection_goals.delete_many({"guild": str(guild.id)})

@client.command(pass_context=True)
@commands.has_permissions(administrator=True) #ensure that only administrators can use this command
async def changeprefix(ctx, prefix):
    filter = { '_id': str(ctx.guild.id) }
 
    # Values to be updated.
    newvalues = { "$set": { 'prefix': prefix } } #using the set command, change the prefix to given string
    
    # Using update_one() method for single updation.
    collection_prefixes.update_one(filter, newvalues)

@client.event
async def on_ready(): #give heads up that the bot is ready and the reminder check is starting
    print("logged in")
    send_reminder.start();

@tasks.loop(minutes=1) 
async def send_reminder():
    # check goals collection
    # if user is due for a reminder
    # send reminder
    # else do nothing
    print("checking now")
    docs = collection_goals.find()
    for doc in docs:
        if doc["level"] == 2:
            now = datetime.now()
            # if time is 30 minutes past 
            if (now - doc["start_time"]).total_seconds() % 1800 == 0:
                user_id = doc["user"]
                user = await client.fetch_user(user_id)
                await user.send("<@" + str(user_id) + "> reminder to focus, are you on track?")
                print(f"message sent to {user_id}")


@client.command()
async def startsession(ctx):
    #important functions of the bot are sent in embedded messages
    #replies are sent with normal messages

    embed = discord.Embed(title="Session Start", color=embed_colour, description="What are your goals for today? (Seperate your goals with commas and no space)")
    embed.set_thumbnail(url="https://64.media.tumblr.com/9bee9543abe86c30cc9b0920c9bdf6ef/tumblr_o908babgn51r4mmz8o1_500.jpg")
    embed.set_footer(text="This bot will need permission to DM you. Please ensure that direct messages from server members are enabled")
    await ctx.send(embed=embed)

    #checking if the user sent a sentence and not just a string of numbers
    def check(author):
        def inner_check(message): 
            if message.author != author:
                return False
            if str(message.content).strip().isdigit():
                return False
            else:
                return True
        return inner_check
    
    #wait for 30 secs before timing out
    msg = await client.wait_for("message", check=check(ctx.author), timeout=30)

    goals_list = msg.content.split(",") #split string by commas (NO SPACES) and create a list
    goals_list_len = len(goals_list)

    #formatting list properly for string
    parse = ""
    i = 0
    for goal in goals_list:
        if (i < goals_list_len - 2):
            parse += goal + ", "
        elif (i == goals_list_len - 2):
            parse += goal + ", and, "
        else:
            parse += goal
        i += 1

    #confirmation with user
    embed = discord.Embed(color=embed_colour, description=f"Fantastic! So you want to `{parse}` today.\nWhat level of checks do you want?\n1: mild, 2: normal")
    msg = await ctx.send(embed=embed)
    
    await msg.add_reaction("1️⃣")
    await msg.add_reaction("2️⃣")

    #check if reactions are of either emoji
    #do something within 30secs
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["1️⃣", "2️⃣"]

    level = 0
    while True:
        reaction, user = await client.wait_for("reaction_add", timeout=30, check=check)

        if str(reaction.emoji) == "1️⃣":
            await ctx.send('Sure! We will check in with you at the end of the session.')
            level = 1
            break

        if str(reaction.emoji) == "2️⃣":
            await ctx.send('Hard worker! We will check in with you every half an hour.')
            level = 2
            break
    
    #format and add data to server for persistance
    start_time = datetime.now()
    collection_goals.insert_one({"user":str(ctx.message.author.id), "guild": str(ctx.guild.id), "goals":goals_list, "level":level, "start_time": start_time})

    msg = await ctx.send(f"<@{ctx.message.author.id}> has started their session!")
    await msg.add_reaction("💪")
    await msg.add_reaction("🌟")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["💪", "🌟"]

    #check if reactions are of either emoji
    #do something within 30secs
    users=""
    while True:
        reaction, user = await client.wait_for("reaction_add", timeout=5, check=check) #TODO: change timeout to realistic number i.e. 60

        if str(reaction.emoji) == "💪":
            msg = await ctx.channel.fetch_message(msg.id)
            # Check our reactions on the message, get user list for the reaction, ignoring the bot
            for reactions in msg.reactions:
                if str(reactions) == "💪":
                    user_list = [user async for user in reactions.users() if user != client.user]
                    # Update the users string, to add user that reacted
                    for user in user_list:
                            users = users + user.mention + "\n"

            usr = await ctx.guild.fetch_member(ctx.author.id)
            await usr.send(f"{users} gave you encouragement for your session! Keep going!")
            break

        if str(reaction.emoji) == "🌟":
            msg = await ctx.channel.fetch_message(msg.id)
            # Check our reactions on the message, get user list for the reaction, ignoring the bot
            for reactions in msg.reactions:
                if str(reactions) == "🌟":
                    user_list = [user async for user in reactions.users() if user != client.user]
                    # Update the users string, to add user that reacted
                    for user in user_list:
                            users = users + user.mention + "\n"

            usr = await ctx.guild.fetch_member(ctx.author.id)
            await usr.send(f"{users} sent you a star for your session! You're stellar!")
            break

@client.command()
async def endsession(ctx):
    user_profile = collection_goals.find_one({"user":str(ctx.message.author.id), "guild": str(ctx.guild.id)})
    user_goals = user_profile["goals"]

    goals_parse = ""
    for g in user_goals:
        goals_parse += f"✅ {g}\n"

    embed = discord.Embed(color=embed_colour,title="Session End",description=f"Have you completed all your goals?\n{goals_parse}")
    msg = await ctx.send(embed=embed)

    await msg.add_reaction("✔️")
    await msg.add_reaction("❌")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✔️", "❌"]

    while True:
            reaction, user = await client.wait_for("reaction_add", timeout=60, check=check) #TODO: change timeout to realistic number i.e. 30

            if str(reaction.emoji) == "✔️":
                await ctx.send('Awesome! Keep up the good work! Remember to get ample sleep, rest, and hydration.')
                break

            if str(reaction.emoji) == "❌":
                await ctx.send('Sometimes we aim for the moon but fall among the stars. Have you made sure your goals are realistic and achievable?')
                break

    collection_goals.delete_one({"user":str(ctx.message.author.id), "guild": str(ctx.guild.id)})

    msg = await ctx.send(f"Send some cheers and encouragement to <@{ctx.message.author.id}>")

    await msg.add_reaction("🎉")
    await msg.add_reaction("🌟")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["🎉", "🌟"]

    users=""
    while True:
        reaction, user = await client.wait_for("reaction_add", timeout=5, check=check) #TODO: change timeout to realistic number i.e. 60

        if str(reaction.emoji) == "🎉":
            msg = await ctx.channel.fetch_message(msg.id)
            reaction_list = msg.reactions
            # Check our reactions on the message, get user list for the reaction, ignoring the bot
            for reactions in msg.reactions:
                if str(reactions) == "🎉":
                    user_list = [user async for user in reactions.users() if user != client.user]
                    # Update the users string, to add user that reacted
                    for user in user_list:
                            users = users + user.mention + "\n"

            usr = await ctx.guild.fetch_member(ctx.author.id)
            await usr.send(f"{users} congratulate you on your session! Absolute champ!")
            break

        if str(reaction.emoji) == "🌟":
            msg = await ctx.channel.fetch_message(msg.id)
            reaction_list = msg.reactions
            # Check our reactions on the message, get user list for the reaction, ignoring the bot
            for reactions in msg.reactions:
                if str(reactions) == "🌟":
                    user_list = [user async for user in reactions.users() if user != client.user]
                    # Update the users string, to add user that reacted
                    for user in user_list:
                            users = users + user.mention + "\n"

            usr = await ctx.guild.fetch_member(ctx.author.id)
            await usr.send(f"{users} sent you a star for your session! Rest well!")
            break

client.run(TOKEN)
