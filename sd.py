# py scrapedata.py

# Grab list of BUIHA IDs

import requests
from bs4 import BeautifulSoup
import time
import random
import json

user_agent = {'User-agent': 'Mozilla/5.0'}

# Look at club page and get ID of every player on current roster for the season
def getPlayerIDs(season):
    # scrape webpage
    r = requests.get('https://buiha.org.uk/club-roster.php?club=18&season=' + season, headers = user_agent)
    soup = BeautifulSoup(r.content, 'html.parser')
    # get all links
    links = [a.get('href') for a in soup.find_all('a', href=True)]
    # filter links for player links
    filtered_links = filter(lambda x: x.startswith("player.php?pid="), links)
    # get player IDs
    ids = map(lambda x: x.split("pid=")[1], filtered_links)
    # filter out duplicates
    unique_ids = list(set(ids))
    # sort IDs by number
    unique_ids.sort()
    return unique_ids

# Get all data into a Player object from a BUIHA player page
def scrapePlayerPage(id: int):

    # scrape webpage
    r = requests.get('https://buiha.org.uk/player.php?pid=' + str(id), headers = user_agent)
    soup = BeautifulSoup(r.content, 'html.parser')
    
    playerObject = ""

    # Player, not a goalie
    if playerType(soup) == "player":
        # Handle name and number
        playerObject = BUIHAPlayer(id, "", "", "", "", "", "", "", "")
        header_text = soup.find('div', id="header_text").find('h1').text.split()

        # Handling inconsistent naming on player pages
        header_list = [i for i in header_text if i != '-' and i != ',' and i != 'LW' and i != 'RW' and i != 'C' and i != 'F' and i != 'D' and (not "," in i)]
        if header_list[0].startswith("#"):
            # player has a number supplied
            playerObject.number = header_list[0]
            header_list.pop(0)
        if len(header_list[len(header_list) - 1]) <= 2:
            # player has a position
            header_list.pop(len(header_list) - 1)
        playerObject.name = " ".join(header_list)

        # Handle games, goals, assists, joined, uni. Takes from player info and main stats banner.
        player_info_div = soup.find('div', id="body_text").find('div').find('div').find_all('div')
        player_info_1 = player_info_div[3].find_all('div') # squad, joined, uni, status
        playerObject.team = player_info_1[1].text[-1]
        playerObject.joined = player_info_1[2].text[-5:]
        playerObject.uni = player_info_1[4].text[12:]
        player_info_2 = player_info_div[10].find_all('div', class_="mbg1")
        
        # Setup for handling large game stats tables
        stat_numbers = []
        stat_links = []
        player_table = soup.find('table', class_="statDetailTable").find_all('td')
        game_links = soup.find('table', class_="statDetailTable").find_all('a')

        # Parse the table into more easily usable data
        for a in game_links:
            newlink = a.get('href')
            if "gid=" in newlink:
                # Get game ID only
                stat_links.append(newlink[-4:])
        # Remove duplicate game IDs
        stat_links = list(dict.fromkeys(stat_links))

        for td in player_table:
            stat_numbers.append(td.text)
        # Remove table labels
        stat_numbers = stat_numbers[11:]
        
        

        player_games = []
        player_seasons = []
        cgame = 0
        # Handle all rows
        while len(stat_numbers) > 10:
            if "/" in stat_numbers[0]:
                # Game
                if len(player_games) <= len(stat_links):
                    player_games.append(stat_numbers[0])
                    new_game = BUIHAPlayerGame(stat_numbers[0], fullName(stat_numbers[4]), homeOrAway(stat_numbers[2]), stat_numbers[5], stat_numbers[6], stat_numbers[7], stat_numbers[9], stat_links[cgame]).__dict__
                    player_games.append(new_game)
                
                    stat_numbers = stat_numbers[14:]
                    cgame += 1
                else:
                    stat_numbers = stat_numbers[14:]
                    cgame += 1
            else:
                # Season
                player_seasons.append(BUIHAPlayerSeason(stat_numbers[0], stat_numbers[1], stat_numbers[2], stat_numbers[3], stat_numbers[4], stat_numbers[6]).__dict__)
                stat_numbers = stat_numbers[11:]

        playerObject.stats_games = player_games
        playerObject.stats_seasons = player_seasons
        
        # collect total stats
        stats_totals = BUIHAPlayerTotal(stat_numbers[1], stat_numbers[2], stat_numbers[3], stat_numbers[4], stat_numbers[5], stat_numbers[6], stat_numbers[7], stat_numbers[8], stat_numbers[9])
        # pims, games, goals, assists
        playerObject.stats_totals = stats_totals.__dict__

    # Goalie. Skater stats are not included, so goalies who play both will only have their goalie stats collected.
    elif playerType(soup) == "goalie":
        playerObject = BUIHAGoalie(id, "", "", "", "", "", "", "", "")

        # Handle name and number
        header_text = soup.find('div', id="header_text").find('h1').text.split()
        header_list = [i for i in header_text if i != '-' and i != ',' and i != 'LW' and i != 'RW' and i != 'C' and i != 'F' and i != 'D' and (not "," in i)]
        if header_list[0].startswith("#"):
            playerObject.number = header_list[0]
            header_list.pop(0)
        if len(header_list[len(header_list) - 1]) == 1:
            header_list.pop(len(header_list) - 1)
        playerObject.name = " ".join(header_list)

        # Handle games, sav%, gaa, 
        player_info_div = soup.find('div', id="body_text").find('div').find('div').find_all('div')
        player_info_1 = player_info_div[3].find_all('div') # squad, joined, uni, status
        playerObject.team = player_info_1[1].text[-1]
        playerObject.joined = player_info_1[2].text[-5:]
        playerObject.uni = player_info_1[4].text[12:]
        player_info_2 = player_info_div[10].find_all('div', class_="mbg1")
        
        stat_numbers = []

        goalie_games = []
        goalie_seasons = []
        stat_links = []
        cgame = 0
        player_table = soup.find('table', class_="statDetailTable").find_all('td')
        game_links = soup.find('table', class_="statDetailTable").find_all('a')

        # Parse the table into more easily usable data
        for a in game_links:
            newlink = a.get('href')
            if "gid=" in newlink:
                # Get game ID only
                stat_links.append(newlink[-4:])
        # Remove duplicate game IDs
        stat_links = list(dict.fromkeys(stat_links))

        for td in player_table:
            stat_numbers.append(td.text)

        stat_numbers = stat_numbers[9:]

        while len(stat_numbers) > 8:
            if "/" in stat_numbers[0]:
                if len(goalie_games) <= len(stat_links):
                    # Game
                    goalie_games.append(BUIHAGoalieGame(stat_numbers[0], fullName(stat_numbers[4]), homeOrAway(stat_numbers[2]), stat_numbers[5], stat_numbers[6], stat_numbers[7], stat_numbers[8], stat_numbers[9], stat_numbers[10], stat_numbers[11], stat_links[cgame]).__dict__)
                    stat_numbers = stat_numbers[12:]
                    cgame += 1
                else: 
                    stat_numbers = stat_numbers[12:]
                    cgame += 1
            else:
                # Season
                goalie_seasons.append(BUIHAGoalieSeason(stat_numbers[0], stat_numbers[1], stat_numbers[2], stat_numbers[3], stat_numbers[4], stat_numbers[5], stat_numbers[6], stat_numbers[7], stat_numbers[8]).__dict__)
                stat_numbers = stat_numbers[9:]

        playerObject.stats_games = goalie_games
        playerObject.stats_seasons = goalie_seasons
        # collect total stats

        stats_totals = BUIHAGoalieTotal(stat_numbers[1], stat_numbers[2], stat_numbers[3], stat_numbers[4], stat_numbers[5], stat_numbers[6], stat_numbers[7])
        # gp, mins, sa, ga, spctt, gaa, so
        playerObject.stats_totals = stats_totals.__dict__

        # Calculate Sav% to 3DP instead of 2. The BUIHA stat works fine but I like this better
        if (stats_totals.sa != ''):
            playerObject.spct = str((int(stats_totals.sa) - int(stats_totals.ga)) / int(stats_totals.sa))[:5]
        else: 
            playerObject.spct = "0.000"

    # Putting BUIHAPlayer / BUIHAGoalie objects into a Player object
    playerObjectJson = Player("", "", "", "", "", "", "", playerObject.__dict__)
    playerObjectJson.id = playerObject.playerID
    playerObjectJson.name = playerObject.name

    # If a number isn't available, #00 is given and won't be displayed on the website
    if playerObject.number != "":
        playerObjectJson.aesthetic_number = playerObject.number
    else: 
        playerObjectJson.aesthetic_number = "#00"
    
    # A team is "Sh. Bears" not "Sh. Bears A", so I need to supply that manually.
    if playerObject.team == 's':
        playerObjectJson.aesthetic_team_pos = "A Team " + playerObject.position
        playerObjectJson.team = "A"
        playerObjectJson.bears_stats["team"] = "A"
    # If they aren't on A team, it's handled normally.
    else:
        playerObjectJson.aesthetic_team_pos = playerObject.team + " Team " + playerObject.position
        playerObjectJson.team = playerObject.team
        playerObjectJson.bears_stats["team"] = playerObject.team
    # Player or Goalie only.
    playerObjectJson.pos = playerObject.position

    return playerObjectJson.__dict__


def playerType(soup):
    if soup.find_all('h1', string="SAV%"):
        return "goalie"
    return "player"


def makeJsonFile(list_of_id, overwrite):
    if overwrite == True:
        json_to_export = []
        for id in list_of_id:
            if len(json_to_export) < 300: # limit to 300 players
                new_scrape = scrapePlayerPage(id)
                print("Completed for", new_scrape.get("name"), "-", (int(list_of_id.index(id)) + 1), "/", len(list_of_id))
                json_to_export.append(new_scrape)
                time.sleep(random.randint(10, 30))

        # write json_to_export to json file
        with open('players.json', 'w') as outfile:
            json.dump(json_to_export, outfile)

def homeOrAway(symbol):
    if symbol == "@":
        return "Away"
    return "Home"
# The data I gather only lists the team's 3 letter code name, not the full name.
# This is a problem as I can't match games to specific squads without also scraping the game page for each game of each player, which would crash their website probably
def fullName(short):
    switcher = {
        "NEW": "Newcastle Wildcats",
        "LEE": "Leeds Gryphons",
        "NOT": "Nottingham Mavericks",
        "BRA": "Bradford Sabres",
        "MAN": "Manchester Metros",
        "BIR": "Birmingham Lions",
        "SHE": "Sheffield Bears",
        "SOU": "Southampton Spitfires",
        "IMP": "Imperial Devils",
        "LON": "London Dragons",
        "COV": "Coventry & Warwick Panthers",
        "NOR": "Northumbria Kings",
        "CAL": "Caledonia Steel Queens",
        "OXF": "Oxford Blues",
        "HUL": "Hull Ice Hogs",
        "ST ": "St Andrews Typhoons",
        "EDI": "Edinburgh Eagles",
        "CAM": "Cambridge Blues",
        "TEA": "Team GB Universities",
        "BUI": "BUIHA Elite Team",
        "WID": "Widnes Wild",
        "UEA": "UEA Avalanche",
        "GLA": "Glasgow Stags",
        "CAR": "Cardiff Redhawks",
        "UCL": "UCL Yetis",
        "UEA": "UEA Avalanche",
        "KIN": "Kingston Diamonds",
        "KEN": "Kent Knights",
    }
    # short, short = input into switcher and default result if not found
    return switcher.get(short, short)


# Class defintions for everything I use to store data
class BUIHAPlayer:
    def __init__(self, playerID, name, uni, team, joined, number, stats_totals, stats_seasons, stats_games):
        self.playerID = playerID
        self.position = "Player"
        self.name = name
        self.uni = uni
        self.team = team
        self.joined = joined
        self.number = number
        self.stats_totals = stats_totals
        self.stats_seasons = stats_seasons
        self.stats_games = stats_games
        
class BUIHAGoalie:
    def __init__(self, playerID, name, uni, team, joined, number, stats_totals, stats_seasons, stats_games):
        self.playerID = playerID
        self.position = "Goalie"
        self.name = name
        self.uni = uni
        self.team = team
        self.joined = joined
        self.number = number
        self.stats_totals = stats_totals
        self.stats_seasons = stats_seasons
        self.stats_games = stats_games
        
class BUIHAPlayerSeason:
    def __init__(self, season, team, gp, g, a, pim):
        self.season = season
        self.team = team
        self.gp = gp
        self.g = g
        self.a = a
        self.pim = pim

class BUIHAPlayerGame:
    def __init__(self, date, opponent, loc, result, g, a, pim, link):
        self.date = date
        self.opponent = opponent
        self.loc = loc
        self.result = result
        self.g = g
        self.a = a
        self.pim = pim
        self.link = link

class BUIHAPlayerTotal:
    def __init__(self, gp, g, a, pts, pim, ppg, shg, gwg, gtg):
        self.gp = gp
        self.g = g
        self.a = a
        self.pts = pts
        self.pim = pim
        self.ppg = ppg
        self.shg = shg
        self.gwg = gwg
        self.gtg = gtg

class BUIHAGoalieSeason:
    def __init__(self, season, team, gp, mins, sa, ga, spct, gaa, so):
        self.season = season
        self.team = team
        self.gp = gp
        self.mins = mins
        self.sa = sa
        self.ga = ga
        self.spct = spct
        self.gaa = gaa
        self.so = so

class BUIHAGoalieGame:
    def __init__(self, date, opponent, loc, result, mins, sa, ga, spct, gaa, so, link):
        self.date = date
        self.opponent = opponent
        self.loc = loc
        self.result = result
        self.mins = mins
        self.sa = sa
        self.ga = ga
        self.spct = spct
        self.gaa = gaa
        self.so = so
        self.link = link

class BUIHAGoalieTotal:
    def __init__(self, gp, mins, sa, ga, spct, gaa, so):
        self.gp = gp
        self.mins = mins
        self.sa = sa
        self.ga = ga
        self.spct = spct
        self.gaa = gaa
        self.so = so

class Player:
    def __init__(self, playerID, name, aesthetic_number, title, aesthetic_team_pos, team, pos, bears_stats):
        self.id = playerID
        self.name = name
        self.aesthetic_number = aesthetic_number
        self.title = title
        self.aesthetic_team_pos = aesthetic_team_pos
        self.team = team
        self.pos = pos
        self.bears_stats = bears_stats

# Function for some fun stats
def activeMembersThroughYears():
    print("08-09", len(getPlayerIDs("08-09")))
    time.sleep(1)
    print("09-10", len(getPlayerIDs("09-10")))
    time.sleep(1)
    print("10-11", len(getPlayerIDs("10-11")))
    time.sleep(1)
    print("11-12", len(getPlayerIDs("11-12")))
    time.sleep(1)
    print("12-13", len(getPlayerIDs("12-13")))
    time.sleep(1)
    print("13-14", len(getPlayerIDs("13-14")))
    time.sleep(1)
    print("14-15", len(getPlayerIDs("14-15")))
    time.sleep(1)
    print("15-16", len(getPlayerIDs("15-16")))
    time.sleep(1)
    print("16-17", len(getPlayerIDs("16-17")))
    time.sleep(1)
    print("17-18", len(getPlayerIDs("17-18")))
    time.sleep(1)
    print("18-19", len(getPlayerIDs("18-19")))
    time.sleep(1)
    print("19-20", len(getPlayerIDs("19-20")))
    time.sleep(1)
    print("21-22", len(getPlayerIDs("21-22")))

def main():
    ### Testing individual player results
    # Carratt - Player, lots of data
    #print(scrapePlayerPage(3813))
    # Zac - Player, small data
    #scrapePlayerPage(6550)
    # Will - NM, lots of data
    #scrapePlayerPage(5250)
    # Jacob - NM, small data
    print(scrapePlayerPage(6335))
    print(scrapePlayerPage(6023))
    print(scrapePlayerPage(5826))
    print(scrapePlayerPage(5250))
    print(scrapePlayerPage(4686))
    #print(scrapePlayerPage(4321))
    ### Main function
    #list_of_id = getPlayerIDs("21-22")
    #print("Looking at player IDs: ", list_of_id)
    #makeJsonFile(list_of_id, True)
    
    #activeMembersThroughYears()

if __name__ == "__main__":
    main()