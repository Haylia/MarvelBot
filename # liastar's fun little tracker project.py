# liastar's fun little tracker project

import discord
import os
import requests
import sys
import json
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# with open ("uids.txt", "r") as file:
#     uids = file.readlines()
#     for i in range(len(uids)):
#         uids[i] = uids[i].strip()
#     print(uids)

# gonna do uids with a dictionary instead of a list, as i need the server name to be the key and the uids (as a list) to be the value
# gonna do this by reading the uids files and getting the server name from the file name
server_uids = {}
uid_channels = {} # to track what channel the uid was added in to post updates
name_uid_cache = {}
uid_update_time = {}
uid_last_known_peak = {}

#every time a max_level is found, compare it to the last known peak and update if it is higher both in the dict and the text file
# then if its higher, post a message in the channel the uid was added in

from discord.ext import commands, tasks
from discord import guild, embeds, Embed, InteractionResponse
from discord.utils import get

intents = discord.Intents.all()
bot_activity = discord.Game(name = "Marble Game")
client = commands.Bot(command_prefix = '$', intents = intents, case_insensitive = True, activity = bot_activity)
timenow = datetime.now()
# driver = webdriver.Chrome()
currentseason = 1

with open("season.txt", "r") as file:
    currentseason = int(file.read())

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    for guilds in client.guilds:
        print(f'Connected to {guilds.name} - {guilds.id}')
        # read from the guilds file and get the uids it contains for each guild, if it exists
        try:
            with open ("uids" + str(guilds.id) + ".txt", "r") as file:
                uids = file.readlines()
                server_uids[guilds.id] = []
                for i in range(len(uids)):
                    # file is formatted uid,channelid
                    uids[i] = uids[i].strip()
                    if uids[i] == "" or uids[i] == " ":
                        continue
                    else:
                        uid, channelid,lastrank,updatetime = uids[i].split(",")
                        server_uids[guilds.id].append(uid)
                        uid_channels[uid] = channelid
                        uid_last_known_peak[uid] = int(lastrank)
                        uid_update_time[uid] = pd.to_datetime(int(updatetime), unit='s')

        except FileNotFoundError:
            print("file not found for " + guilds.name)
            server_uids[guilds.id] = []
            with open ("uids" + str(guilds.id) + ".txt", "w") as file:
                file.write("")
    with open("nameuidcache.txt", "r") as file:
        filelines = file.readlines()
        for line in filelines:
            #first line is blank so skip
            if line == "\n":
                continue
            else:
                line = line.strip()
                uid, name = line.split(",")
                name_uid_cache[uid] = name
                # print(f"added uid {uid} ({name}) to cache")
        print("name uid cache loaded")
            
            
    update_stats.start()

@client.event
async def on_guild_join(guild):
    print(f'Joined a new guild! {guild.name} - {guild.id}')
    # create a file for the uids for this guild
    with open ("uids" + str(guild.id) + ".txt", "w") as file:
        file.write("")
    # add to the dictionary
    server_uids[guild.id] = []
    

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        if type(error) == discord.ext.commands.errors.MemberNotFound:
            await ctx.send("I could not find that member, check the spelling!")    
        else:
            await ctx.send("You made an error in the command arguments")
        print(type(error), error)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You are missing a piece of this command!")
        print(error)
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send("Command failed to run")
        print(error)
    elif isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRole):
        await ctx.send("You do not have the required role to run this command. You need the Head Warden role")
    else:
        await ctx.send("there's an error in this command")
        raise error

def getuidforname(username):
    #check the cache for the username, which is the value
    for key, value in name_uid_cache.items():
        if value.lower() == username.lower():
            return key
    obj = {"name": username}
    response = requests.post("https://rivalsmeta.com/api/find-player", json=obj)
    if response.status_code == 200:
        response = response.json()
        for i in range(len(response)):
            if response[i]["name"].lower() == username.lower():
                username = response[i]["name"]
                uid = response[i]["aid"]
                name_uid_cache[uid] = username
                with open("nameuidcache.txt", "a") as file:
                    file.write(f"\n{uid},{username}")
                return uid
        return "uid finding failed"
    else:
        return "uid finding failed"


def get_stats(username, season = currentseason):
    username = getuidforname(username)
    text, code = buttonclicker(username)
    response = requests.get("https://rivalsmeta.com/api/player/" + username + "?SEASON=" + str(season))
    if response.status_code != 200:
        return "error", "error", "error", "error", "error", "error", "error", "error", "error", "error", "error"
    response = response.json()
    stats = response["stats"]
    rankedwins = stats["ranked_matches_wins"]
    rankedlosses = stats["ranked_matches"] - rankedwins
    timeplayed = stats["ranked"]["total_time_played"] # this is in seconds, we want to convert this to hours to 2 decimal places
    timeplayedhours = int(timeplayed // 3600)
    timeplayedminutes = int((timeplayed % 3600) // 60)
    
    player = response["player"]["info"]
    playername = player["name"]
    teamname = player["club_team_mini_name"]
    level = player["level"]
    season += 1
    try:
        rankgame = player["rank_game_100100" + str(season)]
        rankgame = json.loads(rankgame)
        rank_score = rankgame["rank_game"]["rank_score"]
        rank_score = round(rank_score, 2)
        ranklevel = rankgame["rank_game"]["level"]
        max_rank_score = rankgame["rank_game"]["max_rank_score"]
        max_rank_score = round(max_rank_score, 2)
        max_level = rankgame["rank_game"]["max_level"]
    except:
        # this player has no ranked data for this season
        rank_score = 0
        ranklevel = 0
        max_rank_score = 0
        max_level = 0

    return playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, username



def get_stats_uid(username, season = currentseason):
    text, code = buttonclicker(username)
    response = requests.get("https://rivalsmeta.com/api/player/" + username + "?SEASON=" + str(season))
    if response.status_code != 200:
        return "error", "error", "error", "error", "error", "error", "error", "error", "error", "error", "error"
    response = response.json()
    stats = response["stats"]
    rankedwins = stats["ranked_matches_wins"]
    rankedlosses = stats["ranked_matches"] - rankedwins
    timeplayed = stats["ranked"]["total_time_played"] # this is in seconds, we want to convert this to hours to 2 decimal places
    timeplayedhours = int(timeplayed // 3600)
    timeplayedminutes = int((timeplayed % 3600) // 60)
    
    player = response["player"]["info"]
    playername = player["name"]
    teamname = player["club_team_mini_name"]
    level = player["level"]
    season += 1
    try:
        rankgame = player["rank_game_100100" + str(season)]
        rankgame = json.loads(rankgame)
        rank_score = rankgame["rank_game"]["rank_score"]
        rank_score = round(rank_score, 2)
        ranklevel = rankgame["rank_game"]["level"]
        max_rank_score = rankgame["rank_game"]["max_rank_score"]
        max_rank_score = round(max_rank_score, 2)
        max_level = rankgame["rank_game"]["max_level"]
    except:
        # this player has no ranked data for this season
        rank_score = 0
        ranklevel = 0
        max_rank_score = 0
        max_level = 0
    return playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, username


def convert_level(level):
    # bronze 3-1, silver 3-1, gold 3-1, platinum 3-1, diamond 3-1, grandmaster 3-1, celestial 3-1, anything higher is eternity
    # starts at 1 for bronze 3
    if level < 1:
        return "Unranked"
    elif level < 4:
        return "Bronze " + str(4 - level)
    elif level < 7:
        return "Silver " + str(7 - level)
    elif level < 10:
        return "Gold " + str(10 - level)
    elif level < 13:
        return "Platinum " + str(13 - level)
    elif level < 16:
        return "Diamond " + str(16 - level)
    elif level < 19:
        return "Grandmaster " + str(19 - level)
    elif level < 22:
        return "Celestial " + str(22 - level)
    else:
        return "Eternity"




@client.command(name="uidlookup")
async def uidlookup(ctx, username):
    """Gets the uid for a user based on their username"""
    await ctx.send(getuidforname(username))

@client.command(name="stats")
async def stats(ctx, username, season=1):
    """Gets the stats for a user based on their username"""
    playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats(username, season)
    if playername == "error" and teamname == "error" and level == "error":
        await ctx.send("Failed to get stats for this player")
        return
    # max level spotted!
    peakembed = discord.Embed(title="Congratulations!", color=discord.Color.green())
    peaked = False
    if max_level > uid_last_known_peak[uid]:
        uid_last_known_peak[uid] = max_level
        with open ("uids" + str(ctx.guild.id) + ".txt", "w") as file:
            for i in range(len(server_uids[ctx.guild.id])):
                if server_uids[ctx.guild.id][i] == uid:
                    file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
                else:
                    file.write(f"\n{server_uids[ctx.guild.id][i]},{uid_channels[server_uids[ctx.guild.id][i]]},{uid_last_known_peak[server_uids[ctx.guild.id][i]]},{int(uid_update_time[server_uids[ctx.guild.id][i]].timestamp())}")
        peaked = True
        peakembed.add_field(name=f"{playername} has reached a new peak rank of {convert_level(max_level)}", value=f"New score: {max_rank_score}")
    
    embed = discord.Embed(title=playername + "'s Marvel Rivals Stats", color=discord.Color.blue())
    embed.add_field(name="Faction", value=teamname, inline=False)
    embed.add_field(name="Level", value=level, inline=False)
    rankname = convert_level(ranklevel)
    maxrankname = convert_level(max_level)
    embed.add_field(name="Rank", value=f"{rankname} ({rank_score})\nPeak Rank: {maxrankname} ({max_rank_score})", inline=False)
    if rankedwins + rankedlosses == 0:
        embed.add_field(name="Win/Loss", value="No ranked games played", inline=False)
    else:
        embed.add_field(name="Win/Loss", value=f"{rankedwins}/{rankedlosses} ({round(rankedwins/(rankedwins + rankedlosses) * 100, 2)}%)", inline=False)
    embed.add_field(name="Time Played", value=f"{timeplayedhours}h {timeplayedminutes}m", inline=False)
    await ctx.send(embed=embed)
    if peaked:
        await ctx.send(embed=peakembed)


@client.command(name="statsuid")
async def statsuid(ctx, username, season=1):
    """Gets the stats for a user based on their uid"""
    playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats_uid(username, season)
    if playername == "error" and teamname == "error" and level == "error":
        await ctx.send("No stats found for this player")
        return
    peakembed = discord.Embed(title="Congratulations!", color=discord.Color.green())
    peaked = False
    if max_level > uid_last_known_peak[uid]:
        uid_last_known_peak[uid] = max_level
        with open ("uids" + str(ctx.guild.id) + ".txt", "w") as file:
            for i in range(len(server_uids[ctx.guild.id])):
                if server_uids[ctx.guild.id][i] == uid:
                    file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
                else:
                    file.write(f"\n{server_uids[ctx.guild.id][i]},{uid_channels[server_uids[ctx.guild.id][i]]},{uid_last_known_peak[server_uids[ctx.guild.id][i]]},{int(uid_update_time[server_uids[ctx.guild.id][i]].timestamp())}")
        peaked = True
        peakembed.add_field(name=f"{playername} has reached a new peak rank of {convert_level(max_level)}", value=f"New score: {max_rank_score}")
    embed = discord.Embed(title=playername + "'s Marvel Rivals Stats", color=discord.Color.blue())
    embed.add_field(name="Faction", value=teamname, inline=False)
    embed.add_field(name="Level", value=level, inline=False)
    rankname = convert_level(ranklevel)
    maxrankname = convert_level(max_level)
    embed.add_field(name="Rank", value=f"{rankname} ({rank_score})\nPeak Rank: {maxrankname} ({max_rank_score})", inline=False)
    if rankedwins + rankedlosses == 0:
        embed.add_field(name="Win/Loss", value="No ranked games played", inline=False)
    else:
        embed.add_field(name="Win/Loss", value=f"{rankedwins}/{rankedlosses} ({round(rankedwins/(rankedwins + rankedlosses) * 100, 2)}%)", inline=False)
    embed.add_field(name="Time Played", value=f"{timeplayedhours}h {timeplayedminutes}m", inline=False)
    await ctx.send(embed=embed)
    if peaked:
        await ctx.send(embed=peakembed)
    

@client.command(name="update")
async def update(ctx, username):
    """Asks the API to update the stats for a user based on their username"""
    uid = getuidforname(username)

    text, code = buttonclicker(uid)
    if code == 204:
        await ctx.send(f"update for {uid} ({username}) already done in the last 30 minutes")
    elif code != 200:
        await ctx.send(f"update for {uid} ({username}) failed with code {code}")
    else:
        await ctx.send(f"update for {uid} ({username}) successful")

    jsonresponse = json.loads(text)
    print(jsonresponse)
    if "max_level" in jsonresponse:
        max_level = jsonresponse["info"]["rank_game_100100" + str(currentseason + 1)]["max_level"]
        max_rank_score = jsonresponse["info"]["rank_game_100100" + str(currentseason + 1)]["max_rank_score"]
        playername = jsonresponse["info"]["name"]
    else:
        max_level = 0
        playername = "error"
        await ctx.send("Failed to get peak rank for this player")

    if max_level > uid_last_known_peak[uid]:
        uid_last_known_peak[uid] = max_level
        with open ("uids" + str(ctx.guild.id) + ".txt", "w") as file:
            for i in range(len(server_uids[ctx.guild.id])):
                if server_uids[ctx.guild.id][i] == uid:
                    file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
                else:
                    file.write(f"\n{server_uids[ctx.guild.id][i]},{uid_channels[server_uids[ctx.guild.id][i]]},{uid_last_known_peak[server_uids[ctx.guild.id][i]]},{int(uid_update_time[server_uids[ctx.guild.id][i]].timestamp())}")
        peakembed = discord.Embed(title="Congratulations!", color=discord.Color.green())
        peakembed.add_field(name=f"{playername} has reached a new peak rank of {convert_level(max_level)}", value=f"New score: {max_rank_score}")
        await ctx.send(embed=peakembed)

   
    

@client.command(name="updateuid")
async def updateuid(ctx, uid):
    """Asks the API to update the stats for a user based on their uid"""
    text, code = buttonclicker(uid)
    if code == 204:
        await ctx.send(f"update for {uid} already done in the last 30 minutes")
    elif code != 200:
        await ctx.send(f"update for {uid} failed with code {code}")
    else:
        await ctx.send(f"update for {uid} successful")

    # use the response text to get the max level and player name for the next part
    #the buttonclicker text is response.text
    jsonresponse = json.loads(text)
    if "max_level" in jsonresponse:
        max_level = jsonresponse["info"]["rank_game_100100" + str(currentseason + 1)]["max_level"]
        max_rank_score = jsonresponse["info"]["rank_game_100100" + str(currentseason + 1)]["max_rank_score"]
        playername = jsonresponse["info"]["name"]
    else:
        max_level = 0
        playername = "error"
        await ctx.send("Failed to get peak rank for this player")

    if max_level > uid_last_known_peak[uid]:
        uid_last_known_peak[uid] = max_level
        with open ("uids" + str(ctx.guild.id) + ".txt", "w") as file:
            for i in range(len(server_uids[ctx.guild.id])):
                if server_uids[ctx.guild.id][i] == uid:
                    file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
                else:
                    file.write(f"\n{server_uids[ctx.guild.id][i]},{uid_channels[server_uids[ctx.guild.id][i]]},{uid_last_known_peak[server_uids[ctx.guild.id][i]]},{int(uid_update_time[server_uids[ctx.guild.id][i]].timestamp())}")
        peakembed = discord.Embed(title="Congratulations!", color=discord.Color.green())
        peakembed.add_field(name=f"{playername} has reached a new peak rank of {convert_level(max_level)}", value=f"New score: {max_rank_score}")
        await ctx.send(embed=peakembed)

    
@client.command(name="leaderboard")
async def leaderboard(ctx):
    """Gets the leaderboard for the server"""
    # yo this is the whole idea this is sick
    # loop through the uids, getting their stats and adding them to a list
    # then sort the list by the score
    # then print the list in a discord embed
    embed = discord.Embed(title="Marvel Rivals Leaderboard", color=discord.Color.blue())
    peakembed = discord.Embed(title="Congratulations!", color=discord.Color.green())
    peaked = False
    leaderboard = []
    guildid = ctx.guild.id
    uids = server_uids[guildid]
    if len(uids) == 0:
        await ctx.send("There are no uids being tracked in this server")
        return
    for i in range(len(uids)):
        try:
            if uids[i] == "" or uids[i] == " ":
                continue
            playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats_uid(uids[i])
            if playername == "error" and teamname == "error" and level == "error":
                continue
            else:
                leaderboard.append((playername, teamname, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses))
                if max_level > uid_last_known_peak[uid]:
                    uid_last_known_peak[uid] = max_level
                    with open ("uids" + str(ctx.guild.id) + ".txt", "w") as file:
                        for i in range(len(server_uids[ctx.guild.id])):
                            if server_uids[ctx.guild.id][i] == uid:
                                file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
                            else:
                                file.write(f"\n{server_uids[ctx.guild.id][i]},{uid_channels[server_uids[ctx.guild.id][i]]},{uid_last_known_peak[server_uids[ctx.guild.id][i]]},{int(uid_update_time[server_uids[ctx.guild.id][i]].timestamp())}")
                    peakembed.add_field(name=f"{playername} has reached a new peak rank of {convert_level(max_level)}", value=f"New score: {max_rank_score}")
                    peaked = True
        except:
            print(f"failed to get stats for {uids[i]}")
    leaderboard.sort(key=lambda x: int(x[2]), reverse=True)
    for i in range(len(leaderboard)):
        if leaderboard[i][3] == 0:
            embed.add_field(name=leaderboard[i][0], value="Unranked", inline=False)
        elif leaderboard[i][1] == "":
            embed.add_field(name=leaderboard[i][0], value=f"Rank: {convert_level(leaderboard[i][3])} ({leaderboard[i][2]})\nPeak Rank: {convert_level(leaderboard[i][5])} ({leaderboard[i][4]})\nWin/Loss: {round(leaderboard[i][6]/(leaderboard[i][6] + leaderboard[i][7]) * 100, 2)}% ({leaderboard[i][6]}W {leaderboard[i][7]}L)", inline=False)
        else:
            embed.add_field(name=leaderboard[i][0] + " [" + leaderboard[i][1] + "]", value=f"Rank: {convert_level(leaderboard[i][3])} ({leaderboard[i][2]})\nPeak Rank: {convert_level(leaderboard[i][5])} ({leaderboard[i][4]})\nWin/Loss: {round(leaderboard[i][6]/(leaderboard[i][6] + leaderboard[i][7]) * 100, 2)}% ({leaderboard[i][6]}W {leaderboard[i][7]}L)", inline=False)
    await ctx.send(embed=embed)
    if peaked:
        await ctx.send(embed=peakembed)
    


@client.command(name="add")
async def add(ctx, username):
    """Adds a user to the leaderboard based on their username"""
    guildid = ctx.guild.id
    uid = getuidforname(username)
    if uid == "uid finding failed":
        await ctx.send("Failed to find uid for this player")
        return
    server_uids[guildid].append(uid)
    uid_channels[uid] = ctx.channel.id
    # get stats for the user and add them to the file (for their max rank)
    playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats_uid(uid)
    if playername == "error" and teamname == "error" and level == "error":
        await ctx.send("Failed to get stats for this player")
        return
    uid_last_known_peak[uid] = max_level
    uid_update_time[uid] = datetime.now()
    with open ("uids" + str(guildid) + ".txt", "a") as file:
        file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
    await ctx.send(f"uid {uid} ({playername}) added to the list")
    

@client.command(name="adduid")
async def adduid(ctx, uid):
    """Adds a user to the leaderboard based on their uid"""
    guildid = ctx.guild.id
    #check the uid is valid
    text, code = buttonclicker(uid)
    # good if 200 or 204
    if code != 200 and code != 204:
        await ctx.send(f"Failed to find uid {uid}")
        return
    server_uids[guildid].append(uid)
    uid_channels[uid] = ctx.channel.id
    playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats_uid(uid)
    if playername == "error" and teamname == "error" and level == "error":
        await ctx.send("Failed to get stats for this player")
        return
    uid_last_known_peak[uid] = max_level
    uid_update_time[uid] = datetime.now()
    with open ("uids" + str(guildid) + ".txt", "a") as file:
        file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
    await ctx.send(f"uid {uid} ({playername}) added to the list")

@client.command(name="addlist")
async def addlist(ctx, *usernames):
    """Add a list of usernames to the leaderboard"""
    guildid = ctx.guild.id
    for username in usernames:
        uid = getuidforname(username)
        if uid == "uid finding failed":
            await ctx.send(f"Failed to find uid for {username}")
            continue
        else:
            server_uids[guildid].append(uid)
            uid_channels[uid] = ctx.channel.id
            playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats_uid(uid)
            if playername == "error" and teamname == "error" and level == "error":
                await ctx.send("Failed to get stats for this player")
                return
            uid_last_known_peak[uid] = max_level
            uid_update_time[uid] = datetime.now()
            with open ("uids" + str(guildid) + ".txt", "a") as file:
                file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
            await ctx.send(f"uid {uid} ({playername}) added to the list")

@client.command(name="remove")
async def remove(ctx, username):
    """Removes a user from the leaderboard based on their username"""
    guildid = ctx.guild.id
    uid = getuidforname(username)
    if uid == "uid finding failed":
        await ctx.send("Failed to find uid for this player")
        return
    server_uids[guildid].remove(uid)
    uid_channels.pop(uid)
    with open ("uids" + str(guildid) + ".txt", "w") as file:
        for i in range(len(server_uids[guildid])):
            file.write(f"\n{uid},{str(ctx.channel.id)},{uid_last_known_peak[uid]},{int(datetime.now().timestamp())}")
    await ctx.send(f"uid {uid} ({username}) removed from the list")

@client.command(name="removeuid")
async def removeuid(ctx, uid):
    """Removes a user from the leaderboard based on their uid"""
    guildid = ctx.guild.id
    server_uids[guildid].remove(uid)
    uid_channels.pop(uid)
    with open ("uids" + str(guildid) + ".txt", "w") as file:
        for i in range(len(server_uids[guildid])):
            file.write(f"\n{uid},{str(ctx.channel.id)},{uid_last_known_peak[uid]},{int(datetime.now().timestamp())}")
    await ctx.send(f"uid {uid} removed from the list")

@client.command(name="clearalluids")
async def clearalluids(ctx):
    """Clears all uids from the server"""
    # only lia can do this
    if ctx.author.id != 278288658673434624:
        await ctx.send("You do not have permission to run this command")
        return
    guildid = ctx.guild.id
    server_uids[guildid] = []
    with open ("uids" + str(guildid) + ".txt", "w") as file:
        file.write("")
    await ctx.send("All uids cleared from this server")

@client.command(name="clearalluidsallservers")
async def clearalluidsallservers(ctx):
    """Clears all uids from all servers"""
    # only lia can do this
    if ctx.author.id != 278288658673434624:
        await ctx.send("You do not have permission to run this command")
        return
    for guildid in server_uids:
        server_uids[guildid] = []
        with open ("uids" + str(guildid) + ".txt", "w") as file:
            file.write("")
    await ctx.send("All uids cleared from all servers")


@client.command(name="listuids")
async def listuids(ctx):
    """Lists the uids being tracked in this server"""
    guildid = ctx.guild.id
    uids = server_uids[guildid]
    if len(uids) == 0:
        await ctx.send("There are no uids being tracked in this server")
        return
    message = "The IDs being tracked in this server are: "
    for i in range(len(uids)):
        message += uids[i] + ", "
    # remove the last 2 characters
    message = message[:-2]
    await ctx.send(message)

@client.command(name="listnames")
async def listuidsnames(ctx):
    """Lists the names being tracked in the server"""
    guildid = ctx.guild.id
    uids = server_uids[guildid]
    if len(uids) == 0:
        await ctx.send("There are no uids being tracked in this server")
        return
    message = "The names being tracked in this server are: "
    for i in range(len(uids)):
        playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats_uid(uids[i])
        message += playername + ", "
    # remove the last 2 characters
    message = message[:-2]
    await ctx.send(message)

@client.command(name="setseason")
async def setseason(ctx, season):
    """Sets the current season"""
    # only lia can do this
    if ctx.author.id != 278288658673434624:
        await ctx.send("You do not have permission to run this command")
        return
    global currentseason
    currentseason = int(season)
    with open("season.txt", "w") as file:
        file.write(season)
    await ctx.send(f"Season set to {season}")

@client.command(name="getseason")
async def getseason(ctx):
    """Returns the current season as shown in game"""
    await ctx.send(f"Current season is {currentseason}")

@client.command(name="reportbug")
async def reportbug(ctx, *bug):
    """Reports a bug to the developer"""
    bug = " ".join(bug)
    author = ctx.author
    liadisc = client.get_user(278288658673434624)
    await liadisc.send(f"Bug report from {author}: {bug}")

@client.command(name="suggest")
async def suggest(ctx, *suggestion):
    """Suggests a feature to the developer"""
    suggestion = " ".join(suggestion)
    author = ctx.author
    liadisc = client.get_user(278288658673434624)
    await liadisc.send(f"Suggestion from {author}: {suggestion}")

@client.command(name="announce")
async def announce(ctx, *announcement):
    """Announces something to all servers with an active leaderboard"""
    announcement = " ".join(announcement)
    for guildid in server_uids:
        guild = client.get_guild(guildid)
        for i in range(len(server_uids[guildid])):
            uid = server_uids[guildid][i]
            try:
                await guild.get_channel(int(uid_channels[uid])).send(announcement)
            except:
                print(f"failed to send announcement to {uid}")
    await ctx.send("Announcement sent to all servers")


@tasks.loop(seconds=3600)
async def update_stats():
    global timenow
    timenow = datetime.now()
    # each entry in the dictionary is a list of uids
    for guildid in server_uids:
        uids = server_uids[guildid]
        for i in range(len(uids)):
            try:
                if uids[i] == "" or uids[i] == " ":
                    continue
                playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats_uid(uids[i])
                if playername == "error" and teamname == "error" and level == "error":
                    continue
                else:
                    if max_level > uid_last_known_peak[uid]:
                        uid_last_known_peak[uid] = max_level
                        with open ("uids" + str(guildid) + ".txt", "w") as file:
                            for i in range(len(server_uids[guildid])):
                                if server_uids[guildid][i] == uid:
                                    file.write(f"\n{uid},{str(uid_channels[uid])},{max_level},{int(datetime.now().timestamp())}")
                                else:
                                    file.write(f"\n{server_uids[guildid][i]},{uid_channels[server_uids[guildid][i]]},{uid_last_known_peak[server_uids[guildid][i]]},{int(uid_update_time[server_uids[guildid][i]].timestamp())}")
                        peakembed = discord.Embed(title="Congratulations!", color=discord.Color.green())
                        peakembed.add_field(name=f"{playername} has reached a new peak rank of {convert_level(max_level)}", value=f"New score: {max_rank_score}")
                        await uid_channels[uid].send(embed=peakembed)
            except:
                print(f"failed to get stats for {uids[i]}")
    print("stats updated")




def buttonclicker(uid):
    try: 
        if uid == "" or uid == " ":
            return "uid is empty", 404

        timenow = datetime.now()
        if uid in uid_update_time:
            if (timenow - uid_update_time[uid]).seconds < 1800:
                return "update already done in last 30 minutes", 204
        uid_update_time[uid] = timenow
        response = requests.get("https://rivalsmeta.com/api/update-player/" + str(uid))
        return response.text, response.status_code
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


client.run(TOKEN)