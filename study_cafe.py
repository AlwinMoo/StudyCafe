import os
import discord
from pymongo import MongoClient
from discord.ext import commands
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

def get_prefix(client, message): ##first we define get_prefix
    # with open('prefixes.json', 'r') as f: ##we open and read the prefixes.json, assuming it's in the same file
    #     prefixes = json.load(f) #load the json as prefixes
    # return prefixes[str(message.guild.id)] #recieve the prefix for the guild id given
    document = collection_prefixes.find_one({"_id": str(message.guild.id)})
    return str(document["prefix"])

client = commands.Bot(command_prefix = (get_prefix),)

#client = discord.Client()

@client.event
async def on_guild_join(guild): #when the bot joins the guild
    str_record = {"_id": str(guild.id), "prefix": "sc!"}
    collection_prefixes.insert_one(str_record)
    # with open('prefixes.json', 'r') as f: #read the prefix.json file
    #     prefixes = json.load(f) #load the json file

    # prefixes[str(guild.id)] = 'sc!'#default prefix

    # with open('prefixes.json', 'w') as f: #write in the prefix.json "message.guild.id": "bl!"
    #     json.dump(prefixes, f, indent=4) #the indent is to make everything look a bit neater

    # with open('goals.json', 'w') as f:
    #     parse = {str(guild.id):{}}
    #     json.dump(parse, f, indent=4)

@client.event
async def on_guild_remove(guild): #when the bot is removed from the guild
    collection_prefixes.delete_one({"_id": str(guild.id)})
    # with open('prefixes.json', 'r') as f: #read the file
    #     prefixes = json.load(f)

    # prefixes.pop(str(guild.id)) #find the guild.id that bot was removed from

    # with open('prefixes.json', 'w') as f: #deletes the guild.id as well as its prefix
    #     json.dump(prefixes, f, indent=4)

@client.command(pass_context=True)
@commands.has_permissions(administrator=True) #ensure that only administrators can use this command
async def changeprefix(ctx, prefix): #command: bl!changeprefix ...
    filter = { '_id': str(ctx.guild.id) }
 
    # Values to be updated.
    newvalues = { "$set": { 'prefix': prefix } }
    
    # Using update_one() method for single updation.
    collection_prefixes.update_one(filter, newvalues)

    # with open('prefixes.json', 'r') as f:
    #     prefixes = json.load(f)

    # prefixes[str(ctx.guild.id)] = prefix

    # with open('prefixes.json', 'w') as f: #writes the new prefix into the .json
    #     json.dump(prefixes, f, indent=4)

    # await ctx.send(f'Prefix changed to: {prefix}') #confirms the prefix it's been changed to

@client.command()
async def startsession(ctx):
    embed = discord.Embed(title="Session Start", color=0xFF5733, description="What are your goals for today? (Seperate your goals with commas and no space)")
    embed.set_thumbnail(url="https://64.media.tumblr.com/9bee9543abe86c30cc9b0920c9bdf6ef/tumblr_o908babgn51r4mmz8o1_500.jpg")
    await ctx.send(embed=embed)
    #await ctx.send("What are your goals for today? (Seperate your goals with commas)")

    def check(author):
        def inner_check(message): 
            if message.author != author:
                return False
            if str(message.content).strip().isdigit():
                return False
            else:
                return True
        return inner_check
                
    msg = await client.wait_for("message", check=check(ctx.author), timeout=30)

    goals_list = msg.content.split(",")
    goals_list_len = len(goals_list)

    parse = ""
    i = 0
    for goal in goals_list:
        if (i < goals_list_len - 2):
            parse += goal + ","
        elif (i == goals_list_len - 2):
            parse += goal + ", and "
        else:
            parse += goal
        i += 1

    embed = discord.Embed(color=0xFF5733, description=f"Fantastic! So you want to `{parse}` today.\nWhat level of checks do you want?\n1: mild, 2: normal")
    msg = await ctx.send(embed=embed)
    # await ctx.send("Fantastic!")
    # await ctx.send(f"So you want to `{parse}` today.")
    # msg = await ctx.send(f"What level of checks do you want?\n 1: mild, 2: normal")
    
    await msg.add_reaction("1️⃣")
    await msg.add_reaction("2️⃣")

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
    
    collection_goals.insert_one({"user":str(ctx.message.author.id), "guild": str(ctx.guild.id), "goals":str(goals_list), "level":level})

client.run(TOKEN)