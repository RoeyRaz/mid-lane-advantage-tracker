import requests
import pandas as pd
from sqlalchemy import create_engine
import time

# הגדרות שרת המשחקים (Riot API Configuration)
# Note: Replace with your own API key and Riot ID
API_KEY = "YOUR_RIOT_API_KEY_HERE"
ROUTING_REGION = "europe"
GAME_NAME = "YOUR_RIOT_ID_NAME"
TAG_LINE = "YOUR_RIOT_ID_TAG"
HEADERS = {"X-Riot-Token": API_KEY}

# הגדרות מסד הנתונים (MySQL Configuration)
# Note: Replace with your local database credentials
DB_USER = "root"
DB_PASSWORD = "YOUR_MYSQL_PASSWORD_HERE"
DB_HOST = "localhost"
DB_PORT = "3305"
DB_NAME = "lol_analytics"

# שלב ראשון: חילוץ מזהה השחקן (Get PUUID)
account_url = f"https://{ROUTING_REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{GAME_NAME}/{TAG_LINE}"
account_res = requests.get(account_url, headers=HEADERS)
puuid = account_res.json()["puuid"]
print("PUUID fetched successfully.")

# שלב שני: משיכת 20 מזהי המשחקים האחרונים (Fetch Match IDs)
matches_url = f"https://{ROUTING_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=20"
matches_res = requests.get(matches_url, headers=HEADERS)
match_ids = matches_res.json()
print(f"Found {len(match_ids)} matches. Starting data extraction...")

parsed_records = []

# שלב שלישי: לולאה לאיסוף ולסינון הנתונים (Data Processing Loop)
for match_id in match_ids:
    match_url = f"https://{ROUTING_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    match_res = requests.get(match_url, headers=HEADERS)
    
    # דילוג למשחק הבא במקרה של שגיאה זמנית בשרת (Error handling)
    if match_res.status_code != 200:
        continue
        
    match_data = match_res.json()
    participants = match_data["info"]["participants"]
    game_duration_min = round(match_data["info"]["gameDuration"] / 60, 2)
    
    for p in participants:
        if p.get("teamPosition") == "MIDDLE":
            record = {
                "match_id": match_id,
                "game_duration_min": game_duration_min,
                "player_name": p.get("riotIdGameName", p.get("summonerName")),
                "champion": p["championName"],
                "team_id": p["teamId"],
                "win": int(p["win"]),
                "kills": p["kills"],
                "deaths": p["deaths"],
                "assists": p["assists"],
                "gold_earned": p["goldEarned"],
                "total_minions_killed": p["totalMinionsKilled"],
                "damage_to_champions": p["totalDamageDealtToChampions"]
            }
            parsed_records.append(record)
            
    # המתנה של שנייה כדי לשמור על מגבלת הבקשות של השרת (Time sleep)
    time.sleep(1)

df = pd.DataFrame(parsed_records)

# שלב רביעי: העברה ישירה למסד הנתונים (Load to Database)
connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(connection_string)

df.to_sql(name="mid_matchups", con=engine, if_exists="append", index=False)

print("--- Pipeline execution completed successfully ---")
