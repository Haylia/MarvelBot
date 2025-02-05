# liastar's fun little tracker project

import discord
import os
import requests
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




def get_stats(username):

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


    response = requests.get("https://rivalsmeta.com/player/" + username)
    print(response.status_code)
    # this is the html of the page
    # the info we want is the player name - which is given in the title section in the format <title>username Profile - Marvel Rivals Tracker</title>
    # this is always line 3 in the html
    response_text = response.text
    response_text = response_text.split("\n")
    # print(response_text[2])
    # we want to get the username from the title
    title = response_text[2]
    title = title.split(" ")
    print(title)
    # remove <title> from the start
    title[0] = title[0][7:]
    # remove the last 5 elements of title
    title = title[:-5]
    name = " ".join(title)

    # now in line 22 we have a massive string of essentially useless data but the stat we are interested in is there
    # we want to find the section looking like this 
    # <div class="rank-info"><div class="name">Grandmaster 3</div><div class="score">4,509 <span>score</span></div></div>
    # we want to get the rank info name and the score
    # we can find this by looking for the string "<div class="profile-overview">"

    try:
        rankline = response_text[21]
    except:
        return "rankline not found"
    # we want to split this line by the "<div class="profile-overview">" string
    try:

        rankline = rankline.split('<div class="profile-overview"')
    except:
        return "profile overview split failed"
    # now we want to split the first element of this list by the "<div class="rank-info">" string
    try:
        rankline = rankline[1].split('<div class="rank-info"')
    except:
        with open ("error.txt", "w") as file:
            for i in range(len(rankline)):
                file.write("rankline line " + str(i) + " " + rankline[i] + "\n")
        return "rank info split failed"
    
    # now we want to split the first element of this list by the "<div class="name">" string
    
    rankname = rankline[1].split("<div class=\"name\">")
    rankname = rankname[1].split("</div>")[0]

    ranknumber = rankline[1].split("<div class=\"score\">")
    ranknumber = ranknumber[1].split("<span>")[0].replace(",", "").replace(" ", "")

    rankwl = rankline[1].split("<div class=\"w-l\">")
    rankwl = rankwl[1].split("</div>")[0].replace("<span>", "").replace("</span>", "").replace(" ", "")

    # now we want to clean these up
    # rankname = rankname[1].split("</div>")[0]
    # ranknumber = ranknumber[1].split("</div>")[0]


    return name, rankname, ranknumber, rankwl

def get_stats_uid(username):
    response = requests.get("https://rivalsmeta.com/player/" + username)
    print(response.status_code)
    # this is the html of the page
    # the info we want is the player name - which is given in the title section in the format <title>username Profile - Marvel Rivals Tracker</title>
    # this is always line 3 in the html
    response_text = response.text
    response_text = response_text.split("\n")
    # print(response_text[2])
    # we want to get the username from the title
    title = response_text[2]
    title = title.split(" ")
    print(title)
    # remove <title> from the start
    title[0] = title[0][7:]
    # remove the last 5 elements of title
    title = title[:-5]
    name = " ".join(title)

    # now in line 22 we have a massive string of essentially useless data but the stat we are interested in is there
    # we want to find the section looking like this 
    # <div class="rank-info"><div class="name">Grandmaster 3</div><div class="score">4,509 <span>score</span></div></div>
    # we want to get the rank info name and the score
    # we can find this by looking for the string "<div class="profile-overview">"

    try:
        rankline = response_text[21]
    except:
        return "rankline not found"
    # we want to split this line by the "<div class="profile-overview">" string
    try:

        rankline = rankline.split('<div class="profile-overview"')
    except:
        return "profile overview split failed"
    # now we want to split the first element of this list by the "<div class="rank-info">" string
    try:
        rankline = rankline[1].split('<div class="rank-info"')
    except:
        with open ("error.txt", "w") as file:
            for i in range(len(rankline)):
                file.write("rankline line " + str(i) + " " + rankline[i] + "\n")
        return "rank info split failed"
    
    # now we want to split the first element of this list by the "<div class="name">" string
    
    rankname = rankline[1].split("<div class=\"name\">")
    rankname = rankname[1].split("</div>")[0]

    ranknumber = rankline[1].split("<div class=\"score\">")
    ranknumber = ranknumber[1].split("<span>")[0].replace(",", "").replace(" ", "")

    rankwl = rankline[1].split("<div class=\"w-l\">")
    rankwl = rankwl[1].split("</div>")[0].replace("<span>", "").replace("</span>", "").replace(" ", "")

    # now we want to clean these up
    # rankname = rankname[1].split("</div>")[0]
    # ranknumber = ranknumber[1].split("</div>")[0]


    return name, rankname, ranknumber, rankwl



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
async def stats(ctx, username):
    name, rankname, ranknumber, rankwl = get_stats(username)
    await ctx.send(f"{name} is {rankname} ({ranknumber})\n win/loss: {rankwl}")

@client.command(name="statsuid")
async def statsuid(ctx, username):
    name, rankname, ranknumber, rankwl = get_stats_uid(username)
    await ctx.send(f"{name} is {rankname} ({ranknumber})\n win/loss: {rankwl}")

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
            name, rankname, ranknumber, rankwl = get_stats_uid(uids[i])
            leaderboard.append((name, rankname, ranknumber, rankwl))
        except:
            print(f"failed to get stats for {uids[i]}")
    leaderboard.sort(key=lambda x: int(x[2]), reverse=True)
    for i in range(len(leaderboard)):
        embed.add_field(name=leaderboard[i][0], value=f"{leaderboard[i][1]} ({leaderboard[i][2]})\n win/loss: {leaderboard[i][3]}", inline=False)
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