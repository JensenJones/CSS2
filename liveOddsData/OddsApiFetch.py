import os
import requests
from typing import Dict, Tuple


def fetch_odds(sport_key: str):
    """
    Fetch upcoming matches odds for a given sport key
    and print best odds per team across all bookmakers.
    """
    apiKey = os.getenv("ODDS_API_KEY")
    if not apiKey:
        raise ValueError("Set your ODDS_API_KEY environment variable first!")

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"

    params = {
        "apiKey": apiKey,
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

        # Track best odds: team -> (bestPrice, bookmakerName)
        bestOdds: Dict[str, Tuple[float, str]] = {
            homeTeam: (0.0, ""),
            awayTeam: (0.0, "")
        }

        for bookmaker in event.get("bookmakers", []):
            bookieName = bookmaker.get("title", "")

            for market in bookmaker.get("markets", []):
                if market.get("key") != "h2h":
                    continue

                for outcome in market.get("outcomes", []):
                    teamName = outcome["name"]
                    price = outcome["price"]

                    # Only care about the two teams (ignore draws if present)
                    if teamName not in bestOdds:
                        continue

                    currentBest, _ = bestOdds[teamName]

                    if price > currentBest:
                        bestOdds[teamName] = (price, bookieName)

        # Output
        print(f"{homeTeam} vs {awayTeam}")

        homePrice, homeBookie = bestOdds[homeTeam]
        awayPrice, awayBookie = bestOdds[awayTeam]

        print(f"Best {homeTeam}: {homePrice} @ {homeBookie}")
        print(f"Best {awayTeam}: {awayPrice} @ {awayBookie}")
        print()