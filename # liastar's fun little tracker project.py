# liastar's fun little tracker project

import discord
import os
import requests
import sys
import json
import traceback
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.firefox.service import Service as FirefoxService
# from webdriver_manager.firefox import GeckoDriverManager
# options = webdriver.FirefoxOptions()
# options.add_argument('-headless')
# options.add_argument('-no-sandbox')
# options.add_argument('-disable-gpu')
# options.add_argument('-disable-exensions')
# options.add_argument('-dns-prefetch-disable')
# driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

from selenium.webdriver.chrome.service import Service


service = Service(executable_path="./webdriver/chromedriver")
# service = Service()

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')
options.add_argument('--disable-extensions')
options.add_argument('--dns-prefetch-disable')
options.add_argument('--disable-dev-shm-usage')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)


driver = webdriver.Chrome(service=service, options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
print(driver.execute_script("return navigator.userAgent;"))
driver.maximize_window()

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
author_names = {}

#uid channels needs redoing. it needs to be a dictionary of lists, with the uid as the key and the list of channels as the value
# this is because a user can be tracked in multiple channels in the same server
# all file writing using this will need to be updated to reflect this change (in peak function)

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


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    # this file may not exist:
    try:
        with open("season.txt", "r") as file:
            global currentseason
            currentseason = int(file.read())

    except FileNotFoundError:
        print("season file not found, creating it")
        with open("season.txt", "w") as file:
            file.write(currentseason)
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
                        channelid = int(channelid)
                        server_uids[guilds.id].append(uid)
                        # uid_channels[uid] = channelid # this needs to be a dictionary of lists
                        if uid in uid_channels:
                            uid_channels[uid].append(channelid)
                        else:
                            uid_channels[uid] = [channelid]
                        if uid in uid_last_known_peak:
                            if int(lastrank) > uid_last_known_peak[uid]:
                                uid_last_known_peak[uid] = int(lastrank)
                        else:
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
    try:
        with open("authornames.txt", "r") as file:
            filelines = file.readlines()
            for line in filelines:
                if line == "\n":
                    continue
                else:
                    line = line.strip()
                    authorid, uid = line.split(",")
                    authorid = int(authorid)
                    author_names[authorid] = uid
                    print(f"added author {authorid} to uid {uid}")
            print("author names loaded")
    except FileNotFoundError:
        print("author names file not found")
        with open("authornames.txt", "w") as file:
            file.write("")
        print("author names file created")

    #update_stats.start()

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
        print(f"Command: {message.content} sent by {message.author.name} in {message.guild.name}")
        await client.process_commands(message)

def getuidforname(username):
    #check the cache for the username, which is the value
    global name_uid_cache
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
    
def getnameforuid(uid):
    global name_uid_cache
    if uid in name_uid_cache:
        return name_uid_cache[uid]
    else:
        playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats_uid(uid)
        if playername == "error" and teamname == "error" and level == "error":
            return "Failed to find this player"
        name_uid_cache[uid] = playername
        with open("nameuidcache.txt", "a") as file:
            file.write(f"\n{uid},{playername}")
        print(f"added uid {uid} ({playername}) to cache")
        return playername


def get_stats(username, season=-1):
    if season == -1:
        season = get_current_season()
    username = getuidforname(username)
    print(f"getting stats for {username} in season {season}")
    response = requests.get("https://rivalsmeta.com/api/player/" + username + "?SEASON=" + str(season))
    if response.status_code != 200:
        return "error", "error", "error", "error", "error", "error", "error", "error", "error", "error", "error", "error"
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
        #print(rankgame)
        rankgame = json.loads(rankgame)
        rank_score = rankgame["rank_game"]["rank_score"]
        rank_score = round(rank_score, 2)
        ranklevel = rankgame["rank_game"]["level"]
        max_rank_score = rankgame["rank_game"]["max_rank_score"]
        max_rank_score = round(max_rank_score, 2)
        max_level = rankgame["rank_game"]["max_level"]
    except Exception as e:
        # this player has no ranked data for this season
        print(f"no ranked data for {playername} in season {season}")
        rank_score = 0
        ranklevel = 0
        max_rank_score = 0
        max_level = 0

    return playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, username



def get_stats_uid(username, season=-1):
    if season == -1:
        season = get_current_season()
    response = requests.get("https://rivalsmeta.com/api/player/" + username + "?SEASON=" + str(season))
    if response.status_code != 200:
        return "error", "error", "error", "error", "error", "error", "error", "error", "error", "error", "error", "error"
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
    except Exception as e:
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
    1217: "Central Park",
}

def get_map(mapid):
    return map_dict.get(int(mapid), "Unknown Map " + str(mapid))

hero_dict = {
    1011: "Bruce Banner",
    1014: "The Punisher",
    1015: "Storm",
    1016: "Loki",
    1017: "Human Torch",
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
    1051: "The Thing",
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
            print(f"uid {uid} has reached a new peak rank of {convert_level(max_level)}")
            for guilds in client.guilds:
                guildid = guilds.id
                channelids = uid_channels[uid]
                # if the uid is tracked in the guild, send the message to the channel
                if str(uid) in server_uids[guildid] :
                    print(f"sending peak message for {uid} in {guilds.name}")
                    for channels in channelids:
                        # if the channel is in the guild, send the message
                        channel = client.get_channel(channels)
                        if channel in guilds.channels:
                            channelid = channel.id
                            break
                    peakembed = discord.Embed(title="Congratulations!", color=discord.Color.green())
                    with open ("uids" + str(guildid) + ".txt", "r") as file:
                        oldlines = file.readlines()
                    with open ("uids" + str(guildid) + ".txt", "w") as file:
                        for line in oldlines:
                            if line == "\n" or line == " " or line == "":
                                file.write(line)
                            else:
                                fileuid, channelid,lastrank,updatetime = line.split(",")
                                if fileuid == str(uid):
                                    file.write(f"{uid},{channelid},{max_level},{int(uid_update_time[uid].timestamp())}\n")
                                else:
                                    file.write(line)
                        # for i in range(len(server_uids[guildid])):
                        #     if server_uids[guildid][i] == uid:
                        #         file.write(f"\n{uid},{str(channelid)},{max_level},{int(datetime.now().timestamp())}")
                        #     else:
                        #         # find the channelid for this uid for this guild
                        #         # since uid_channels is a dictionary of lists, we need to loop through the list to find the channelid
                        #         channelfound = False
                        #         for j in range(len(uid_channels[uid])):
                        #             if uid_channels[uid][j] == channelid:
                        #                 file.write(f"\n{server_uids[guildid][i]},{uid_channels[uid][j]},{uid_last_known_peak[uid]},{int(uid_update_time[uid].timestamp())}")
                        #                 channelfound = True
                        #                 break
                        #         if not channelfound:
                        #             for channel in guilds.channels:
                        #                 if channel.id in uid_channels[uid]:
                        #                     file.write(f"\n{server_uids[guildid][i]},{channel.id},{uid_last_known_peak[uid]},{int(uid_update_time[uid].timestamp())}")
                        #                     break

                    peaked = True
                    peakembed.add_field(name=f"{playername} has reached a new peak rank of {convert_level(max_level)}", value=f"New score: {max_rank_score}")
                    embeds_to_send.append(peakembed)
                    returnchannels.append(channelid)
        return embeds_to_send, peaked, returnchannels
    else:
        return None, False, None
    
def get_author_names():
    global author_names
    return author_names
    
@client.command(name="matches")
async def matches(ctx, username="", amount=5):
    """Gets match history for a user"""
    if amount > 10:
        await ctx.send("You can only display up to 10 matches at a time")
        return
    global author_names
    authorused = False
    if username == "":
        authorid = ctx.author.id
        if authorid in author_names:
            username = author_names[authorid]
            playername = getnameforuid(username)
            authorused = True
        else:
            await ctx.send("You have not set a username to track. Use the " + PREFIX + "set command to set your username, or provide a username")
            return
    else:
        playername = username
    if not authorused:
        username = getuidforname(username)
    for key, value in name_uid_cache.items():
        if value.lower() == playername.lower():
            playername = value
    
    response = requests.get("https://rivalsmeta.com/api/player/" + username + "?SEASON=" + str(get_current_season))
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
            if deaths == 0:
                kda = "Perfect"
            else:
                kda = round(int(kills + assists)/int(deaths),2)
            embed.add_field(name=f"{mapname} - {gamemode} (<t:{matchtimestamp}:R>)" + leftstring, value=f"{winstring} as {playerheroname}{vpstring}\n KDA {kills}/{deaths}/{assists} ({kda}){rankstring}\nScore: {scoreteam0} - {scoreteam1} in {matchtimemins}m {matchtimesecs}s", inline=False)
    embed.set_footer(text="Last updated: " + uid_update_time[username].strftime('%Y-%m-%d %H:%M:%S'))
    await ctx.send(embed=embed)


@client.command(name="uidlookup")
async def uidlookup(ctx, username=""):
    """Gets the uid for a user based on their username"""
    global author_names
    if username == "":
        authorid = ctx.author.id
        if authorid in author_names:
            username = author_names[authorid]
            await ctx.send(username)
            return
        else:
            await ctx.send("You have not set a username to track. Use the " + PREFIX + "set command to set your username, or provide a username")
            return
    await ctx.send(getuidforname(username))

@client.command(name="namelookup")
async def namelookup(ctx, uid):
    """Gets the name for a user based on their uid"""
    await ctx.send(getnameforuid(uid))
    

@client.command(name="stats")
async def stats(ctx, username="", season=-1):
    """Gets the stats for a user based on their username"""
    global author_names
    if username == "":
        #print("no username provided")
        authorid = ctx.author.id
        if authorid in author_names:
            username = getnameforuid(author_names[authorid])
            #print(f"username is {username}")
        else:
            await ctx.send("You have not set a username to track. Use the " + PREFIX + "set command to set your username, or provide a username")
            return
    if season == -1:
        season = get_current_season()
    playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats(username, season)
    if playername == "error" and teamname == "error" and level == "error":
        await ctx.send("Failed to get stats for this player")
        return
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
    embed.set_footer(text="Last updated: " + uid_update_time[uid].strftime('%Y-%m-%d %H:%M:%S'))
    await ctx.send(embed=embed)
    if peaked:
        for i in range(len(peakchannels)):
            channel = client.get_channel(int(peakchannels[i]))
            await channel.send(embed=peakembeds[i])


@client.command(name="statsuid")
async def statsuid(ctx, username="", season=-1):
    """Gets the stats for a user based on their uid"""
    global author_names
    if username == "":
        authorid = ctx.author.id
        if authorid in author_names:
            username = author_names[authorid]
        else:
            await ctx.send("You have not set a username to track. Use the " + PREFIX + "set command to set your username, or provide a username")
            return
    if season == -1:
        season = get_current_season()
    playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats_uid(username, season)
    if playername == "error" and teamname == "error" and level == "error":
        await ctx.send("No stats found for this player")
        return
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
    embed.set_footer(text="Last updated: " + uid_update_time[uid].strftime('%Y-%m-%d %H:%M:%S'))
    await ctx.send(embed=embed)
    if peaked:
        # return the peakembed to the corresponding peakchannel
        for i in range(len(peakchannels)):
            channel = client.get_channel(int(peakchannels[i]))
            await channel.send(embed=peakembeds[i])
    

@client.command(name="update")
async def update(ctx, username=""):
    """Asks the API to update the stats for a user based on their username"""
    # if the username is not provided, get the author's uid from the author names dict
    global author_names
    if username == "":
        authorid = ctx.author.id
        if authorid in author_names:
            uid = author_names[authorid]
            username = getnameforuid(uid)
        else:
            await ctx.send("You have not set a username to track. Use the " + PREFIX + "set command to set your username, or provide a username")
            return
    else:
        uid = getuidforname(username)
    text, code = buttonclicker(uid)
    if code == 204:
        await ctx.send(f"update for {uid} ({username}) already done in the last 30 minutes. Last updated at {uid_update_time[uid].strftime('%Y-%m-%d %H:%M:%S')}")
    elif code != 200:
        await ctx.send(f"update for {uid} ({username}) failed with code {code}")
    else:
        await ctx.send(f"update for {uid} ({username}) successful")
        # jsonresponse = json.loads(text)
        # if "max_level" in jsonresponse:
        #     max_level = jsonresponse["info"]["rank_game_100100" + str(currentseason)]["max_level"]
        #     max_rank_score = jsonresponse["info"]["rank_game_100100" + str(currentseason)]["max_rank_score"]
        #     playername = jsonresponse["info"]["name"]
        # else:
        #     max_level = 0
        #     playername = "error"
        #     await ctx.send("Failed to get peak rank for this player")
# 
        # peakembeds, peaked, peakchannels = peak_embed_creator(uid, playername, max_level, max_rank_score)
        # if peaked:
        #     for i in range(len(peakchannels)):
        #         channel = client.get_channel(int(peakchannels[i]))
        #         await channel.send(embed=peakembeds[i])

   
    

@client.command(name="updateuid")
async def updateuid(ctx, uid=""):
    """Asks the API to update the stats for a user based on their uid"""
    global author_names
    if uid == "":
        authorid = ctx.author.id
        if authorid in author_names:
            uid = author_names[authorid]
        else:
            await ctx.send("You have not set a username to track. Use the " + PREFIX + "set command to set your username, or provide a username")
            return
    text, code = buttonclicker(uid)
    if code == 204:
        await ctx.send(f"update for {uid} already done in the last 30 minutes")
    elif code != 200:
        await ctx.send(f"update for {uid} failed with code {code}")
    else:
        await ctx.send(f"update for {uid} successful")

    # use the response text to get the max level and player name for the next part
    #the buttonclicker text is response.text
    #     jsonresponse = json.loads(text)
    #     if "max_level" in jsonresponse:
    #         max_level = jsonresponse["info"]["rank_game_100100" + str(currentseason)]["max_level"]
    #         max_rank_score = jsonresponse["info"]["rank_game_100100" + str(currentseason)]["max_rank_score"]
    #         playername = jsonresponse["info"]["name"]
    #     else:
    #         max_level = 0
    #         playername = "error"
    #         await ctx.send("Failed to get peak rank for this player")
    # 
    #     peakembeds, peaked, peakchannels = peak_embed_creator(uid, playername, max_level, max_rank_score)
    #     if peaked:
    #         for i in range(len(peakchannels)):
    #             channel = client.get_channel(int(peakchannels[i]))
    #             await channel.send(embed=peakembeds[i])

    
@client.command(name="leaderboard")
async def leaderboard(ctx):
    """Gets the leaderboard for the server"""
    # yo this is the whole idea this is sick
    # loop through the uids, getting their stats and adding them to a list
    # then sort the list by the score
    # then print the list in a discord embed
    embed = discord.Embed(title="Marvel Rivals Leaderboard", color=discord.Color.blue())
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
                await ctx.send("There are no uids being tracked in this server")
                return
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
        if leaderboard[i][6] + leaderboard[i][7] == 0:
            winrate = "N/A"
        else:
            winrate = round(leaderboard[i][6]/(leaderboard[i][6] + leaderboard[i][7]) * 100, 2)
        if leaderboard[i][3] == 0:
            embed.add_field(name=leaderboard[i][0], value="Unranked", inline=False)
        elif leaderboard[i][1] == "":
            embed.add_field(name=leaderboard[i][0], value=f"Rank: {convert_level(leaderboard[i][3])} ({leaderboard[i][2]})\nPeak Rank: {convert_level(leaderboard[i][5])} ({leaderboard[i][4]})\nWin/Loss: {winrate}% ({leaderboard[i][6]}W {leaderboard[i][7]}L)", inline=False)
        else:
            embed.add_field(name=leaderboard[i][0] + " [" + leaderboard[i][1] + "]", value=f"Rank: {convert_level(leaderboard[i][3])} ({leaderboard[i][2]})\nPeak Rank: {convert_level(leaderboard[i][5])} ({leaderboard[i][4]})\nWin/Loss: {winrate}% ({leaderboard[i][6]}W {leaderboard[i][7]}L)", inline=False)
    await ctx.send(embed=embed)
    if peaked:
        for i in range(len(peakchannels)):
            channel = client.get_channel(int(peakchannels[i]))
            await channel.send(embed=peakembeds[i])
    


    

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
    if uid in server_uids[guildid]:
        await ctx.send(f"{uid} is already being tracked")
        return
    server_uids[guildid].append(uid)
    if uid in uid_channels:
        uid_channels[uid].append(ctx.channel.id)
    else:
        uid_channels[uid] = [ctx.channel.id]
    playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes, uid = get_stats_uid(uid)
    if playername == "error" and teamname == "error" and level == "error":
        await ctx.send("Failed to get stats for this player")
        return
    uid_last_known_peak[uid] = max_level
    uid_update_time[uid] = datetime.now()
    with open ("uids" + str(guildid) + ".txt", "a") as file:
        file.write(f"\n{uid},{str(ctx.channel.id)},{max_level},{int(datetime.now().timestamp())}")
    await ctx.send(f"uid {uid} ({playername}) added to the list")

@client.command(name="add")
async def add(ctx, *usernames):
    """Add a list of usernames to the leaderboard"""
    guildid = ctx.guild.id
    for username in usernames:
        uid = getuidforname(username)
        if uid == "uid finding failed":
            await ctx.send(f"Failed to find uid for {username}")
            continue
        else:
            if uid in server_uids[guildid]:
                await ctx.send(f"{username} is already being tracked")
            else:
                server_uids[guildid].append(uid)
                if uid in uid_channels:
                    uid_channels[uid].append(ctx.channel.id)
                else:
                    uid_channels[uid] = [ctx.channel.id]
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
    if uid not in server_uids[guildid]:
        await ctx.send(f"{username} is not being tracked")
        return
    server_uids[guildid].remove(uid)
    uid_channels.pop(uid)
    with open ("uids" + str(guildid) + ".txt", "w") as file:
        for i in range(len(server_uids[guildid])):
            file.write(f"\n{server_uids[guildid][i]},{str(ctx.channel.id)},{uid_last_known_peak[server_uids[guildid][i]]},{int(datetime.now().timestamp())}")
    await ctx.send(f"uid {uid} ({username}) removed from the list")

@client.command(name="removeuid")
async def removeuid(ctx, uid):
    """Removes a user from the leaderboard based on their uid"""
    guildid = ctx.guild.id
    server_uids[guildid].remove(uid)
    users_channels = uid_channels[uid]
    if uid not in server_uids[guildid]:
        await ctx.send(f"{uid} is not being tracked")
        return
    for i in range(len(users_channels)):
        if users_channels[i] == ctx.channel.id:
            users_channels.pop(i)
            break
    with open ("uids" + str(guildid) + ".txt", "w") as file:
        for i in range(len(server_uids[guildid])):
            file.write(f"\n{server_uids[guildid][i]},{str(ctx.channel.id)},{uid_last_known_peak[server_uids[guildid][i]]},{int(datetime.now().timestamp())}")
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

def get_ingame_season():
    global currentseason
    if int(currentseason) == 1:
        return 0
    elif int(currentseason) == 2:
        return 1
    elif int(currentseason) == 3:
        return 1.5
    

def get_current_season():
    global currentseason
    return currentseason

@client.command(name="getseason")
async def getseason(ctx):
    """Returns the current season as shown in game"""
    await ctx.send(f"Current season is {get_ingame_season()} (Bot: {get_current_season()})")

@client.command(name="reportbug")
async def reportbug(ctx, *bug):
    """Reports a bug to the developer"""
    bug = " ".join(bug)
    author = ctx.author
    liadisc = client.get_user(278288658673434624)
    await liadisc.send(f"Bug report from {author}: {bug}")
    await ctx.send("Bug report sent")

@client.command(name="bugreport")
async def bugreport(ctx, *bug):
    """Reports a bug to the developer"""
    bug = " ".join(bug)
    author = ctx.author
    liadisc = client.get_user(278288658673434624)
    await liadisc.send(f"Bug report from {author} ({author.id}): {bug}")
    await ctx.send("Bug report sent")

@client.command(name="suggest")
async def suggest(ctx, *suggestion):
    """Suggests a feature to the developer"""
    suggestion = " ".join(suggestion)
    author = ctx.author
    liadisc = client.get_user(278288658673434624)
    await liadisc.send(f"Suggestion from {author} ({author.id}): {suggestion}")
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
    # uid_channels is a dictionary with the uid as the key and the channelids as a list as the value
    uniquechannels = []
    for key, value in uid_channels.items():
        for i in range(len(value)):
            if value[i] not in uniquechannels:
                uniquechannels.append(value[i])

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
    if PREFIX == "#":
        embed.add_field(name="wONSTIN", value="I was created as a test bench bot for Winston, Lia's DKP bot for Paranoid and then for Relentless. Now I just test everything Lia is working on, so my functionality is always changing.", inline=False)
    else:
        embed.add_field(name="Marvel Rarvels", value="This bot is still in development. Please use the " + PREFIX + "reportbug and the " + PREFIX + "suggest commands to help improve the bot", inline=False)
    await ctx.send(embed=embed)


@client.command(name="set")
async def set(ctx, username):
    """Sets the default username for this user"""
    author_names = get_author_names()
    author = ctx.author
    uid = getuidforname(username)
    oldname = ""
    if author.id in author_names:
        oldname = getnameforuid(author_names[author.id])
    if oldname.lower() == username.lower():
        await ctx.send(f"{username} is already the default username for {author}")
        return
    if uid == "uid finding failed":
        await ctx.send("Failed to find uid for this player")
        return
    author_names[author.id] = uid
    #print(author_names)
    with open ("authornames.txt", "w") as file:
        for key, value in author_names.items():
            file.write(f"\n{key},{value}")
            #print(f"added {key},{value} to file")
    if oldname == "":
        await ctx.send(f"Default username for {author} set to {username}")
    else:
        await ctx.send(f"Default username for {author} changed from {oldname} to {username}")

@client.command(name="me")
async def me(ctx):
    """Gets the default username for this user, plus memes?"""
    message = ""
    if ctx.author.id == 122466532960763906:
        message += "Real SlugGal!\n"
    elif ctx.author.id == 278288658673434624:
        message += "Liasto statline\n"
    elif ctx.author.id == 220951788277202944:
        message += "Hi Dalish!!!!\n"
    elif ctx.author.id == 106131363018575872:
        message += "the moom hauah youoy\n"
    elif ctx.author.id == 355523578432585728:
        message += "meow :3\n"
    elif ctx.author.id == 235599271770980353:
        message += "Hi Spy!!!!\n"
    author_names = get_author_names()
    author = ctx.author
    if author.id in author_names:
        message += "Your set username is: " + getnameforuid(author_names[author.id])
        await ctx.send(message)
    else:
        message += "You have not set a default username"
        await ctx.send(message)

@client.command(name="senddm")
async def senddm(ctx, user, *message):
    """[ADMIN] Sends a DM to a user"""
    # only lia can do this
    if ctx.author.id != 278288658673434624:
        await ctx.send("You do not have permission to run this command")
        return
    message = " ".join(message)
    user = client.get_user(int(user))
    await user.send(message)
    await ctx.send("DM sent")

@client.command(name="debuggetmaxlevel")
async def debuggetmaxlevel(ctx, username):
    """Gets the max level for a user based on their username"""
    uid = getuidforname(username)
    if uid == "uid finding failed":
        await ctx.send("Failed to find uid for this player")
    else:
        if uid in uid_last_known_peak:
            await ctx.send(f"Max level for {username} is {uid_last_known_peak[uid]} ({convert_level(uid_last_known_peak[uid])})")


@client.command(name="cachedelete")
async def cachedelete(ctx, username):
    """[ADMIN] Deletes a name from the cache"""
    # only lia can do this
    if ctx.author.id != 278288658673434624:
        await ctx.send("You do not have permission to run this command")
        return
    for key, value in name_uid_cache.items():
        if value.lower() == username.lower():
            name_uid_cache.pop(key)
            await ctx.send(f"{username} removed from the cache")
            # write the cache to the file
            with open("nameuidcache.txt", "w") as file:
                for key, value in name_uid_cache.items():
                    file.write(f"{key},{value}\n")
            return
    await ctx.send(f"{username} not found in the cache")
        



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
        try:
            global driver
            # catch empty session (invalid id) caused by tab crashing:
            crashed = True
            while crashed:
                try:
                    print("getting player page for " + uid)
                    driver.get("https://rivalsmeta.com/player/" + uid)
                    crashed = False
                except:
                    print("crashed, attempting to restart driver")
                    global service
                    service = Service(executable_path="./webdriver/chromedriver")
                    # service = Service()
                    global options
                    driver.quit()
                    driver = webdriver.Chrome(service=service, options=options)
                    driver.maximize_window()
            print("Updating Player " + uid)
            # firefox
            # button = driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/section/div[1]/div[1]/div[2]/div')
            # chrome
            button = driver.find_element(By.XPATH, '//*[@id="__nuxt"]/div[2]/section/div[1]/div[1]/div[2]/div/button/span')
            try:
                #firefox
                #timerele = driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/section/div[1]/div[1]/div[2]/div/div')
                #chrome
                timerele = driver.find_element(By.XPATH, '//*[@id="__nuxt"]/div[2]/section/div[1]/div[1]/div[2]/div/div')
            except:
                # sometimes this element is not visible, so we will just click the button and move on.
                timerele = button
            # if the button is already clicked, we don't want to click it again. timerele is only visible if the button has been clicked
            if "Available in" in timerele.text:
                print(f"button already clicked for {uid}. {timerele.text}")
                return "button already clicked", 204
            button.click()
            print("Button clicked on Player " + uid)
            uid_update_time[uid] = timenow
            # write the update time to the relevant files for this uid
            for guildid in server_uids:
                if uid in server_uids[guildid]:
                    with open ("uids" + str(guildid) + ".txt", "r") as file:
                        oldlines = file.readlines()
                    with open ("uids" + str(guildid) + ".txt", "w") as file:
                        for line in oldlines:
                            if uid in line:
                                # find the channel id for this uid in this guild
                                line = line.strip()
                                line = line.split(",")
                                channelid = line[1]
                                file.write(f"{uid},{str(channelid)},{uid_last_known_peak[uid]},{int(datetime.now().timestamp())}\n")
                            else:
                                file.write(line)
            print("update time written to file")

                                
        except Exception as e:
            print(e)
            return "button click failed", 500
        return "button clicked", 200
        # response2 = requests.get("https://rivalsmeta.com/api/update-player/" + str(uid))
        # response = requests.get("https://rivalsmeta.com/api/update-player/" + str(uid) + "?SEASON=" + str(currentseason))
        #print(response2.text)
        # write the update time to the relevant file for this uid
        #print(response.text)
        #return response.text, response.status_code
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


client.run(TOKEN)