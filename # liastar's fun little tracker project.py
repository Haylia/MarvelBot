# liastar's fun little tracker project

import discord
import os
import requests
import sys
import json
import traceback
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('DISCORD_PREFIX')


# gonna do uids with a dictionary instead of a list, as i need the server name to be the key and the uids (as a list) to be the value
# gonna do this by reading the uids files and getting the server name from the file name
server_uids = {}
uid_channels = {} # to track what channel the uid was added in to post updates
name_uid_cache = {}
uid_update_time = {}
uid_last_known_peak = {}

#every time a max_level is found, compare it to the last known peak and update if it is higher both in the dict and the text file
# then if its higher, post a message in the channel the uid was added in
# current logic problems: 
# if the uid is not being tracked in the server it breaks everything
# solution: check if the uid is tracked in the server before trying to update it
# extra solution: 

# when a new peak is achieved, it only gets posted in the channel that trigged the update
# solution: check all the other servers uids to post in there too
# extra solution: turn the peak message into a function that can be called from anywhere

from discord.ext import commands, tasks
from discord import guild, embeds, Embed, InteractionResponse
from discord.utils import get

intents = discord.Intents.all()
bot_activity = discord.Game(name = "Marble Game")
# Change only the no_category default string
help_command = commands.DefaultHelpCommand(
    no_category = 'Commands'
)
client = commands.Bot(command_prefix = PREFIX, intents = intents, case_insensitive = True, activity = bot_activity, help_command=help_command)
timenow = datetime.now()
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
                        print(f"added uid {uid} to {guilds.name} with last known peak {lastrank} and update time {uid_update_time[uid].strftime('%Y-%m-%d %H:%M:%S')}")

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
        #print out the line number that the error happened on
        # error with traceback is error.with_traceback
        print(error)
        traceback.print_exception(type(error), error, error.__traceback__)
    elif isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRole):
        await ctx.send("You do not have the required role to run this command. You need the Head Warden role")
    else:
        await ctx.send("there's an error in this command")
        raise error
    
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith(PREFIX):
        print(f"Command: {message.content}")
        await client.process_commands(message)

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
        return "Bronze " + str(4 - int(level))
    elif level < 7:
        return "Silver " + str(7 - int(level))
    elif level < 10:
        return "Gold " + str(10 - int(level))
    elif level < 13:
        return "Platinum " + str(13 - int(level))
    elif level < 16:
        return "Diamond " + str(16 - int(level))
    elif level < 19:
        return "Grandmaster " + str(19 - int(level))
    elif level < 22:
        return "Celestial " + str(22 - int(level))
    else:
        return "Eternity"
    
map_dict = {
    1272: "Birnin T'Challa",
    1288: "Hell's Heaven",
    1291: "Midtown",
    1231: "Yggdrasill Path",
    1236: "Royal Palace",
    1245: "Spider-Islands",
    1240: "Symbiotic Surface",
    1230: "Shin-Shibuya",
    1267: "Hall of Djalia",
    1290: "Symbiotic Surface",
}

def get_map(mapid):
    return map_dict.get(int(mapid), "Unknown Map " + str(mapid))

hero_dict = {
    1011: "Bruce Banner",
    1014: "The Punisher",
    1015: "Storm",
    1016: "Loki",
    1018: "Doctor Strange",
    1020: "Mantis",
    1021: "Hawkeye",
    1022: "Captain America",
    1023: "Rocket Raccoon",
    1024: "Hela",
    1025: "Cloak and Dagger",
    1026: "Black Panther",
    1027: "Groot",
    1029: "Magik",
    1030: "Moon Knight",
    1031: "Luna Snow",
    1032: "Squirrel Girl",
    1033: "Black Widow",
    1034: "Iron Man",
    1035: "Venom",
    1036: "Spider-Man",
    1037: "Magneto",
    1038: "Scarlet Witch",
    1039: "Thor",
    1040: "Mister Fantastic",
    1041: "Winter Soldier",
    1042: "Peni Parker",
    1043: "Star-Lord",
    1045: "Namor",
    1046: "Adam Warlock",
    1047: "Jeff the Land Shark",
    1048: "Psylocke",
    1049: "Wolverine",
    1050: "Invisible Woman",
    1052: "Iron Fist"
}

def get_hero_name(heroid):
    return hero_dict.get(heroid, "Unknown Hero " + str(heroid))

def convert_game_mode(camp):
    if camp == 1:
        return "Quick Match"
    elif camp == 2:
        return "Ranked"
    else:
        return "Other"
    
def peak_embed_creator(uid, playername, max_level, max_rank_score):
    embeds_to_send = []
    returnchannels = []
    peaked = False
    if uid in uid_last_known_peak:
        if max_level > uid_last_known_peak[uid]:
            # we are going to be changing this function to return a list of embeds to send to all the guilds the user is tracked in
            # so we will find the guilds, and then the associated channels. update the peak in the dict and the file
            # and then add the embed to the list of embeds to return
            peakembed = discord.Embed(title="Congratulations!", color=discord.Color.green())
            uid_last_known_peak[uid] = max_level
            for guilds in client.guilds:
                guildid = guilds.id
                if uid in server_uids[guildid]:
                    channelid = uid_channels[uid]
                    with open ("uids" + str(guildid) + ".txt", "w") as file:
                        for i in range(len(server_uids[guildid])):
                            if server_uids[guildid][i] == uid:
                                file.write(f"\n{uid},{str(channelid)},{max_level},{int(datetime.now().timestamp())}")
                            else:
                                file.write(f"\n{server_uids[guildid][i]},{uid_channels[server_uids[guildid][i]]},{uid_last_known_peak[server_uids[guildid][i]]},{int(uid_update_time[server_uids[guildid][i]].timestamp())}")
                    peaked = True
                    peakembed.add_field(name=f"{playername} has reached a new peak rank of {convert_level(max_level)}", value=f"New score: {max_rank_score}")
                    embeds_to_send.append(peakembed)
                    returnchannels.append(channelid)
        return embeds_to_send, peaked, returnchannels
    else:
        return None, False, None
    
    
@client.command(name="matches")
async def matches(ctx, username, amount=5):
    """Gets match history for a user"""
    if amount > 10:
        await ctx.send("You can only display up to 10 matches at a time")
        return
    playername = username
    username = getuidforname(username)
    for key, value in name_uid_cache.items():
        if value.lower() == playername.lower():
            playername = value
    
    response = requests.get("https://rivalsmeta.com/api/player/" + username + "?SEASON=" + str(currentseason))
    if response.status_code != 200:
        await ctx.send("Failed to get match history for this player")
        return
    response = response.json()
    matchhistory = response["match_history"]
    if len(matchhistory) == 0:
        await ctx.send("No matches found for this player")
        return
    embed = discord.Embed(title=playername + "'s Match History", color=discord.Color.blue())
    for i in range(amount):
            match = matchhistory[i]
            mapname = get_map(match["match_map_id"])
            matchtimer = int(match["match_play_duration"])
            matchtimestamp = int(match["match_time_stamp"])
            mvp = match["mvp_uid"]
            svp = match["svp_uid"]
            dynamicfields = match["dynamic_fields"]
            scoreinfo = dynamicfields["score_info"]
            if scoreinfo == None:
                scoreteam0 = "N/A"
                scoreteam1 = "N/A"
            else:
                scoreteam0 = int(scoreinfo["0"])
                scoreteam1 = int(scoreinfo["1"])
            gamemode = convert_game_mode(match["game_mode_id"])
            matchplayerinfo = match["match_player"]
            assists = matchplayerinfo["a"]
            deaths = matchplayerinfo["d"]
            kills = matchplayerinfo["k"]
            playerwon = matchplayerinfo["is_win"]
            didleave = matchplayerinfo["has_escaped"]
            dynamicfields2 = matchplayerinfo["dynamic_fields"]
            scoreadded = dynamicfields2["add_score"]
            oldlevel = dynamicfields2["level"]
            newlevel = dynamicfields2["new_level"]
            newscore = dynamicfields2["new_score"]
            playerhero = matchplayerinfo["player_hero"]
            playerheroid = playerhero["hero_id"]
            playerheroname = get_hero_name(playerheroid)
            playerismvp = str(username) == str(mvp)
            playerissvp = str(username) == str(svp)
            vpstring = ""
            winstring = ""
            leftstring = ""
            if playerismvp:
                vpstring += " (MVP)"
            elif playerissvp:
                vpstring += " (SVP)"
            if playerwon == 1:
                winstring += "Won"
            else:
                winstring += "Lost"
            if didleave:
                leftstring += " [Left]"
            matchtimemins = (matchtimer) // 60
            matchtimesecs = matchtimer % 60
            scorestr = ""
            if scoreadded > 0:
                scorestr = "+"
            rankstring = ""
            if gamemode == "Ranked":
                rankstring = f"\nRank: {convert_level(oldlevel)} -> {convert_level(newlevel)}\nRS: {round(float(newscore), 2)} ({scorestr}{round(float(scoreadded), 2)})"
            embed.add_field(name=f"{mapname} - {gamemode} (<t:{matchtimestamp}:R>)" + leftstring, value=f"{winstring} as {playerheroname}{vpstring}\n KDA {kills}/{deaths}/{assists} ({round(int(kills + assists)/int(deaths),2)}){rankstring}\nScore: {scoreteam0} - {scoreteam1} in {matchtimemins}m {matchtimesecs}s", inline=False)
    await ctx.send(embed=embed)


@client.command(name="uidlookup")
async def uidlookup(ctx, username):
    """Gets the uid for a user based on their username"""
    await ctx.send(getuidforname(username))

@client.command(name="stats")
async def stats(ctx, username, season=currentseason):
    """Gets the stats for a user based on their username"""
    playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats(username, season)
    if playername == "error" and teamname == "error" and level == "error":
        await ctx.send("Failed to get stats for this player")
        return
    # max level spotted!
    # peakembed = discord.Embed(title="Congratulations!", color=discord.Color.green())
    # peaked = False
    # if max_level > uid_last_known_peak[uid]:
    #     uid_last_known_peak[uid] = max_level
    #     with open ("uids" + str(ctx.guild.id) + ".txt", "w") as file:
    #         for i in range(len(server_uids[ctx.guild.id])):
    #             if server_uids[ctx.guild.id][i] == uid:
    #                 file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
    #             else:
    #                 file.write(f"\n{server_uids[ctx.guild.id][i]},{uid_channels[server_uids[ctx.guild.id][i]]},{uid_last_known_peak[server_uids[ctx.guild.id][i]]},{int(uid_update_time[server_uids[ctx.guild.id][i]].timestamp())}")
    #     peaked = True
    #     peakembed.add_field(name=f"{playername} has reached a new peak rank of {convert_level(max_level)}", value=f"New score: {max_rank_score}")
    peakembeds, peaked, peakchannels = peak_embed_creator(uid, playername, max_level, max_rank_score)
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
        for i in range(len(peakchannels)):
            channel = client.get_channel(int(peakchannels[i]))
            await channel.send(embed=peakembeds[i])


@client.command(name="statsuid")
async def statsuid(ctx, username, season=currentseason):
    """Gets the stats for a user based on their uid"""
    playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats_uid(username, season)
    if playername == "error" and teamname == "error" and level == "error":
        await ctx.send("No stats found for this player")
        return
    # peakembed = discord.Embed(title="Congratulations!", color=discord.Color.green())
    # peaked = False
    # if max_level > uid_last_known_peak[uid]:
    #     uid_last_known_peak[uid] = max_level
    #     with open ("uids" + str(ctx.guild.id) + ".txt", "w") as file:
    #         for i in range(len(server_uids[ctx.guild.id])):
    #             if server_uids[ctx.guild.id][i] == uid:
    #                 file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
    #             else:
    #                 file.write(f"\n{server_uids[ctx.guild.id][i]},{uid_channels[server_uids[ctx.guild.id][i]]},{uid_last_known_peak[server_uids[ctx.guild.id][i]]},{int(uid_update_time[server_uids[ctx.guild.id][i]].timestamp())}")
    #     peaked = True
    #     peakembed.add_field(name=f"{playername} has reached a new peak rank of {convert_level(max_level)}", value=f"New score: {max_rank_score}")
    peakembeds, peaked, peakchannels = peak_embed_creator(uid, playername, max_level, max_rank_score)
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
        # return the peakembed to the corresponding peakchannel
        for i in range(len(peakchannels)):
            channel = client.get_channel(int(peakchannels[i]))
            await channel.send(embed=peakembeds[i])
    

@client.command(name="update")
async def update(ctx, username):
    """Asks the API to update the stats for a user based on their username"""
    uid = getuidforname(username)

    text, code = buttonclicker(uid)
    if code == 204:
        await ctx.send(f"update for {uid} ({username}) already done in the last 30 minutes. Last updated at {uid_update_time[uid].strftime('%Y-%m-%d %H:%M:%S')}")
    elif code != 200:
        await ctx.send(f"update for {uid} ({username}) failed with code {code}")
    else:
        await ctx.send(f"update for {uid} ({username}) successful")
        jsonresponse = json.loads(text)
        if "max_level" in jsonresponse:
            max_level = jsonresponse["info"]["rank_game_100100" + str(currentseason)]["max_level"]
            max_rank_score = jsonresponse["info"]["rank_game_100100" + str(currentseason)]["max_rank_score"]
            playername = jsonresponse["info"]["name"]
        else:
            max_level = 0
            playername = "error"
            await ctx.send("Failed to get peak rank for this player")

        # if max_level > uid_last_known_peak[uid]:
        #     uid_last_known_peak[uid] = max_level
        #     with open ("uids" + str(ctx.guild.id) + ".txt", "w") as file:
        #         for i in range(len(server_uids[ctx.guild.id])):
        #             if server_uids[ctx.guild.id][i] == uid:
        #                 file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
        #             else:
        #                 file.write(f"\n{server_uids[ctx.guild.id][i]},{uid_channels[server_uids[ctx.guild.id][i]]},{uid_last_known_peak[server_uids[ctx.guild.id][i]]},{int(uid_update_time[server_uids[ctx.guild.id][i]].timestamp())}")
        #     peakembed = discord.Embed(title="Congratulations!", color=discord.Color.green())
        #     peakembed.add_field(name=f"{playername} has reached a new peak rank of {convert_level(max_level)}", value=f"New score: {max_rank_score}")
        #     await ctx.send(embed=peakembed)
        peakembeds, peaked, peakchannels = peak_embed_creator(uid, playername, max_level, max_rank_score)
        if peaked:
            for i in range(len(peakchannels)):
                channel = client.get_channel(int(peakchannels[i]))
                await channel.send(embed=peakembeds[i])

   
    

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
            max_level = jsonresponse["info"]["rank_game_100100" + str(currentseason)]["max_level"]
            max_rank_score = jsonresponse["info"]["rank_game_100100" + str(currentseason)]["max_rank_score"]
            playername = jsonresponse["info"]["name"]
        else:
            max_level = 0
            playername = "error"
            await ctx.send("Failed to get peak rank for this player")
    
        # if max_level > uid_last_known_peak[uid]:
        #     uid_last_known_peak[uid] = max_level
        #     with open ("uids" + str(ctx.guild.id) + ".txt", "w") as file:
        #         for i in range(len(server_uids[ctx.guild.id])):
        #             if server_uids[ctx.guild.id][i] == uid:
        #                 file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
        #             else:
        #                 file.write(f"\n{server_uids[ctx.guild.id][i]},{uid_channels[server_uids[ctx.guild.id][i]]},{uid_last_known_peak[server_uids[ctx.guild.id][i]]},{int(uid_update_time[server_uids[ctx.guild.id][i]].timestamp())}")
        #     peakembed = discord.Embed(title="Congratulations!", color=discord.Color.green())
        #     peakembed.add_field(name=f"{playername} has reached a new peak rank of {convert_level(max_level)}", value=f"New score: {max_rank_score}")
        #     await ctx.send(embed=peakembed)
        peakembeds, peaked, peakchannels = peak_embed_creator(uid, playername, max_level, max_rank_score)
        if peaked:
            for i in range(len(peakchannels)):
                channel = client.get_channel(int(peakchannels[i]))
                await channel.send(embed=peakembeds[i])

    
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
                peakembeds, peaked, peakchannels = peak_embed_creator(uid, playername, max_level, max_rank_score)
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
        for i in range(len(peakchannels)):
            channel = client.get_channel(int(peakchannels[i]))
            await channel.send(embed=peakembeds[i])
    


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
    """[ADMIN] Clears all uids from the server"""
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
    """[ADMIN] Clears all uids from all servers"""
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
    """[ADMIN] Sets the current season"""
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
    await ctx.send("Bug report sent")

@client.command(name="suggest")
async def suggest(ctx, *suggestion):
    """Suggests a feature to the developer"""
    suggestion = " ".join(suggestion)
    author = ctx.author
    liadisc = client.get_user(278288658673434624)
    await liadisc.send(f"Suggestion from {author}: {suggestion}")
    await ctx.send("Suggestion sent")

@client.command(name="announce")
async def announce(ctx, *announcement):
    """[ADMIN] Announces something to all servers with an active leaderboard"""
    # only lia can do this
    if ctx.author.id != 278288658673434624:
        await ctx.send("You do not have permission to run this command")
        return
    announcement = " ".join(announcement)
    # Get all the unique channels in uid_channels
    uniquechannels = list(set(uid_channels.values()))

    # for each guild, check if the channel is in the uniquechannels list
    # if it is, send the announcement to that channel
    for guild in client.guilds:
        if guild.id in server_uids:
            for channel in guild.text_channels:
                if channel.id in uniquechannels or str(channel.id) in uniquechannels:
                    await channel.send(announcement)
    await ctx.send("Announcement sent to all servers")

@client.command(name="about")
async def about(ctx):
    """About this project"""
    embed = discord.Embed(title="Marvel Rivals Bot", color=discord.Color.blue())
    embed.add_field(name="Developer", value="<@278288658673434624>", inline=False)
    embed.add_field(name="Description", value="A bot that tracks Marvel Rivals stats", inline=False)
    await ctx.send(embed=embed)


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
                    peakembeds, peaked, peakchannels = peak_embed_creator(uid, playername, max_level, max_rank_score)
                    if peaked:
                        for i in range(len(peakchannels)):
                            channel = client.get_channel(int(peakchannels[i]))
                            await channel.send(embed=peakembeds[i])
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