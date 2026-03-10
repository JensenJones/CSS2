import os
import requests

# Example usage:
# fetch_odds("table_tennis")
# fetch_odds("basketball_ncaab")
def fetch_odds(sport_key: str):
    """
    Fetch upcoming matches odds for a given sport key.
    """
    API_KEY = os.getenv("ODDS_API_KEY")
    if not API_KEY:
        raise ValueError("Set your ODDS_API_KEY environment variable first!")

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"

    params = {
        "apiKey": API_KEY,
        "regions": "au",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} {response.text}")

    events = response.json()

    for event in events:
        homeTeam = event["home_team"]
        awayTeam = event["away_team"]

        for bookmaker in event["bookmakers"]:
            for market in bookmaker["markets"]:
                if market["key"] != "h2h":
                    continue

                odds = {o["name"]: o["price"] for o in market["outcomes"]}

                print(f"{homeTeam} vs {awayTeam}")
                print(f"{bookmaker['title']} Odds: {odds.get(homeTeam)} / {odds.get(awayTeam)}")
                print()