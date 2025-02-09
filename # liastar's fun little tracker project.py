# liastar's fun little tracker project

import discord
import os
import requests
import sys
import json
from datetime import datetime
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
                for i in range(len(uids)):
                    uids[i] = uids[i].strip()
                server_uids[guilds.id] = uids
        except:
            server_uids[guilds.id] = []
            with open ("uids" + str(guilds.id) + ".txt", "w") as file:
                file.write("")
            
            
    # update_stats.start()

@client.event
async def on_guild_join(guild):
    print(f'Connected to {guild.name} - {guild.id}')
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

#page = urllib.request.urlopen('http://services.runescape.com/m=hiscore/ranking?table=0&category_type=0&time_filter=0&date=1519066080774&user=zezima')
# print(page.read())

# headers = {"TRN-Api-Key": "feaff12e-794d-4bb7-8ef8-5d5435a95080"}
# 
# # we are getting a player's marvel rivals stats
# url = "https://public-api.tracker.gg/v2/marvel-rivals/standard/profile/pc/"
# 
# # build the request
# def get_stats(username):
#     response = requests.get(url + username, headers=headers)
#     print(response.json())
# 
# 
# 
# get_stats("VerityBlue")




def get_stats(username, season = currentseason):

    obj = {"name": username}
    response = requests.post("https://rivalsmeta.com/api/find-player", json=obj)
    if response.status_code == 200:
        # response should look something like this
        # [{"name":"username","aid":"somenumber","cur_head_icon_id":"whocares"}]
        response = response.json()
        #await ctx.send(f"uid for {username} is {response[0]['aid']}")
        username = response[0]['aid']
    else:
        return "post failed"


    response = requests.get("https://rivalsmeta.com/api/player/" + username + "?SEASON=" + str(season))
    print(response.status_code)
    # with open ("response.txt", "w") as file:
    #     file.write(response.text)
    #     print("wrote response to file")
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
    rankgame = player["rank_game_100100" + str(season)]
    # this is the rank game info
    # {"rank_game":{"max_level":16,"rank_score":4488.9095827628,"update_time":1739052363,"protect_score":0,"diff_score":23.933122850863,"rank_game_id":2,"win_count":105,"level":15,"max_rank_score":4565.2217554892}}
    # Extracting information from rankgame
    rankgame = json.loads(rankgame)
    rank_score = rankgame["rank_game"]["rank_score"]
    rank_score = round(rank_score, 2)
    ranklevel = rankgame["rank_game"]["level"]
    max_rank_score = rankgame["rank_game"]["max_rank_score"]
    max_rank_score = round(max_rank_score, 2)
    max_level = rankgame["rank_game"]["max_level"]
    # print(f"ranked wins: {rankedwins} ranked losses: {rankedlosses} time played: {timeplayed} team name: {teamname} level: {level} rank: {rank_score} rank level: {ranklevel} max rank: {max_rank_score} max rank level: {max_level}")
    
    return playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes



def get_stats_uid(username, season = currentseason):
    response = requests.get("https://rivalsmeta.com/api/player/" + username + "?SEASON=" + str(season))
    print(response.status_code)
    # with open ("response.txt", "w") as file:
    #     file.write(response.text)
    #     print("wrote response to file")
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
    rankgame = player["rank_game_100100" + str(season)]
    # this is the rank game info
    # {"rank_game":{"max_level":16,"rank_score":4488.9095827628,"update_time":1739052363,"protect_score":0,"diff_score":23.933122850863,"rank_game_id":2,"win_count":105,"level":15,"max_rank_score":4565.2217554892}}
    # Extracting information from rankgame
    rankgame = json.loads(rankgame)
    rank_score = rankgame["rank_game"]["rank_score"]
    rank_score = round(rank_score, 2)
    ranklevel = rankgame["rank_game"]["level"]
    max_rank_score = rankgame["rank_game"]["max_rank_score"]
    max_rank_score = round(max_rank_score, 2)
    max_level = rankgame["rank_game"]["max_level"]
    # print(f"ranked wins: {rankedwins} ranked losses: {rankedlosses} time played: {timeplayed} team name: {teamname} level: {level} rank: {rank_score} rank level: {ranklevel} max rank: {max_rank_score} max rank level: {max_level}")
    
    return playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes


def convert_level(level):
    # bronze 3-1, silver 3-1, gold 3-1, platinum 3-1, diamond 3-1, grandmaster 3-1, celestial 3-1, anything higher is eternity
    # starts at 1 for bronze 3
    if level < 4:
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
    obj = {"name": username}
    response = requests.post("https://rivalsmeta.com/api/find-player", json=obj)
    if response.status_code == 200:
        # response should look something like this
        # [{"name":"username","aid":"somenumber","cur_head_icon_id":"whocares"}]
        response = response.json()
        await ctx.send(f"uid for {username} is {response[0]['aid']}")
    # await ctx.send(response.text)

@client.command(name="stats")
async def stats(ctx, username, season=1):
    playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes = get_stats(username, season)
    embed = discord.Embed(title=playername + "'s Marvel Rivals Stats", color=discord.Color.blue())
    embed.add_field(name="Faction", value=teamname, inline=False)
    embed.add_field(name="Level", value=level, inline=False)
    rankname = convert_level(ranklevel)
    maxrankname = convert_level(max_level)
    embed.add_field(name="Rank", value=f"{rankname} ({rank_score})\nPeak Rank: {maxrankname} ({max_rank_score})", inline=False)
    embed.add_field(name="Win/Loss", value=f"{rankedwins}/{rankedlosses} ({round(rankedwins/(rankedwins + rankedlosses) * 100, 2)}%)", inline=False)
    embed.add_field(name="Time Played", value=f"{timeplayedhours}h {timeplayedminutes}m", inline=False)
    await ctx.send(embed=embed)


@client.command(name="statsuid")
async def statsuid(ctx, username, season=1):
    playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes = get_stats(username, season)
    embed = discord.Embed(title=playername + "'s Marvel Rivals Stats", color=discord.Color.blue())
    embed.add_field(name="Faction", value=teamname, inline=False)
    embed.add_field(name="Level", value=level, inline=False)
    rankname = convert_level(ranklevel)
    maxrankname = convert_level(max_level)
    embed.add_field(name="Rank", value=f"{rankname} ({rank_score})\nPeak Rank: {maxrankname} ({max_rank_score})", inline=False)
    embed.add_field(name="Win/Loss", value=f"{rankedwins}/{rankedlosses} ({round(rankedwins/(rankedwins + rankedlosses) * 100, 2)}%)", inline=False)
    embed.add_field(name="Time Played", value=f"{timeplayedhours}h {timeplayedminutes}m", inline=False)
    await ctx.send(embed=embed)

@client.command(name="update")
async def update(ctx, username):

    obj = {"name": username}
    response = requests.post("https://rivalsmeta.com/api/find-player", json=obj)
    if response.status_code == 200:
        # response should look something like this
        # [{"name":"username","aid":"somenumber","cur_head_icon_id":"whocares"}]
        response = response.json()
        #await ctx.send(f"uid for {username} is {response[0]['aid']}")
        uid = response[0]['aid']
    else:
        return "post failed"

    text, code = buttonclicker(uid)
    if code != 200:
        await ctx.send(f"update for {uid} failed with code {code}")
    else:
        await ctx.send(f"update for {uid} successful")

@client.command(name="updateuid")
async def updateuid(ctx, uid):

    text, code = buttonclicker(uid)
    if code != 200:
        await ctx.send(f"update for {uid} failed with code {code}")
    else:
        await ctx.send(f"update for {uid} successful")

@client.command(name="leaderboard")
async def leaderboard(ctx):
    # yo this is the whole idea this is sick
    # loop through the uids, getting their stats and adding them to a list
    # then sort the list by the score
    # then print the list in a discord embed
    embed = discord.Embed(title="Marvel Rivals Leaderboard", color=discord.Color.blue())
    leaderboard = []
    guildid = ctx.guild.id
    uids = server_uids[guildid]
    if len(uids) == 0:
        await ctx.send("There are no uids being tracked in this server")
        return
    for i in range(len(uids)):
        text, code = buttonclicker(uids[i])
        if code != 200:
            print(f"failed to get stats for //{uids[i]}//")
            print(text)
            print(code)
        else:
            print(f"update for {uids[i]} successful")
    for i in range(len(uids)):
        try:
            if uids[i] == "" or uids[i] == " ":
                continue
            playername, teamname, level, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses, timeplayedhours, timeplayedminutes = get_stats_uid(uids[i])
            leaderboard.append((playername, teamname, rank_score, ranklevel, max_rank_score, max_level, rankedwins, rankedlosses))
        except:
            print(f"failed to get stats for {uids[i]}")
    leaderboard.sort(key=lambda x: int(x[2]), reverse=True)
    for i in range(len(leaderboard)):
        if leaderboard[i][1] == "":
            embed.add_field(name=leaderboard[i][0], value=f"Rank: {convert_level(leaderboard[i][3])} ({leaderboard[i][2]})\nPeak Rank: {convert_level(leaderboard[i][5])} ({leaderboard[i][4]})\nWin/Loss: {round(leaderboard[i][6]/(leaderboard[i][6] + leaderboard[i][7]) * 100, 2)}% ({leaderboard[i][6]}W {leaderboard[i][7]}L)", inline=False)
        else:
            embed.add_field(name=leaderboard[i][0] + " [" + leaderboard[i][1] + "]", value=f"Rank: {convert_level(leaderboard[i][3])} ({leaderboard[i][2]})\nPeak Rank: {convert_level(leaderboard[i][5])} ({leaderboard[i][4]})\nWin/Loss: {round(leaderboard[i][6]/(leaderboard[i][6] + leaderboard[i][7]) * 100, 2)}% ({leaderboard[i][6]}W {leaderboard[i][7]}L)", inline=False)
    await ctx.send(embed=embed)

@client.command(name="adduid")
async def adduid(ctx, uid):
    guildid = ctx.guild.id
    server_uids[guildid].append(uid)
    with open ("uids" + str(guildid) + ".txt", "a") as file:
        file.write("\n" + uid)
    await ctx.send(f"uid {uid} added to the list")

@client.command(name="removeuid")
async def removeuid(ctx, uid):
    guildid = ctx.guild.id
    server_uids[guildid].remove(uid)
    with open ("uids" + str(guildid) + ".txt", "w") as file:
        for i in range(len(server_uids[guildid])):
            file.write(server_uids[guildid][i] + "\n")
    await ctx.send(f"uid {uid} removed from the list")

@client.command(name="listuids")
async def listuids(ctx):
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

@client.command(name="setseason")
async def setseason(ctx, season):
    global currentseason
    currentseason = int(season)
    with open("season.txt", "w") as file:
        file.write(season)
    await ctx.send(f"Season set to {season}")

@client.command(name="getseason")
async def getseason(ctx):
    await ctx.send(f"Current season is {currentseason}")

        

@tasks.loop(seconds=2000)
async def update_stats():
    global timenow
    timenow = datetime.now()
    for uid in server_uids:
        text, code = buttonclicker(uid)
        print(f"update for {uid} - {text} - {code}")

def buttonclicker(uid):
    # global driver
    # driver.get("https://rivalsmeta.com/player/" + uid)
    # button = driver.find_element(By.CLASS_NAME, "btn-update")
    # button.click()
    if uid == "" or uid == " ":
        return "uid is empty", 404
        
    response = requests.get("https://rivalsmeta.com/api/update-player/" + uid)
    return response.text, response.status_code
    


client.run(TOKEN)