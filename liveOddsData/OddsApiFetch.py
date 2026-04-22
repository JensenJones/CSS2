import os
import requests
from typing import Dict, List, Optional, Tuple


def fetch_active_sports(include_out_of_season: bool = False) -> List[Dict]:
    """
    Returns all sports currently available on the API.
    Uses GET /v4/sports/ — does not count against the usage quota.

    Each dict has keys: key, title, description, active, has_outrights.
    Pass include_out_of_season=True to also get off-season sports.
    """
    apiKey = os.getenv("ODDS_API_KEY")
    if not apiKey:
        raise ValueError("Set your ODDS_API_KEY environment variable first!")

    params: Dict = {"apiKey": apiKey}
    if include_out_of_season:
        params["all"] = "true"

    response = requests.get("https://api.the-odds-api.com/v4/sports/", params=params)
    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} {response.text}")

    return response.json()


def fetch_odds_display(sport_key: str):
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


def fetch_odds_structured(sport_key: str, regions: str = "au") -> List[Dict]:
    """
    Fetch upcoming match odds and return structured data for internal use.
    For each event, finds the best available odds per outcome (home/away/draw)
    across all bookmakers — ready for arbitrage detection.

    Returns a list of dicts with shape:
    {
        "event_id": str,
        "sport": str,
        "commence_time": str,
        "home_team": str,
        "away_team": str,
        "home_odds": float,
        "home_bookie": str,
        "away_odds": float,
        "away_bookie": str,
        "draw_odds": float | None,
        "draw_bookie": str | None,
    }
    """
    apiKey = os.getenv("ODDS_API_KEY")
    if not apiKey:
        raise ValueError("Set your ODDS_API_KEY environment variable first!")

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": apiKey,
        "regions": regions,
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} {response.text}")

    events = response.json()
    structured = []

    for event in events:
        homeTeam = event["home_team"]
        awayTeam = event["away_team"]

        # best odds per outcome: name -> (price, bookie)
        best: Dict[str, Tuple[float, str]] = {}

        for bookmaker in event.get("bookmakers", []):
            bookieName = bookmaker.get("title", "")
            for market in bookmaker.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                for outcome in market.get("outcomes", []):
                    name = outcome["name"]
                    price = outcome["price"]
                    if price > best.get(name, (0.0, ""))[0]:
                        best[name] = (price, bookieName)

        drawEntry: Optional[Tuple[float, str]] = best.get("Draw")

        structured.append({
            "event_id": event.get("id", ""),
            "sport": sport_key,
            "commence_time": event.get("commence_time", ""),
            "home_team": homeTeam,
            "away_team": awayTeam,
            "home_odds": best.get(homeTeam, (None, None))[0],
            "home_bookie": best.get(homeTeam, (None, None))[1],
            "away_odds": best.get(awayTeam, (None, None))[0],
            "away_bookie": best.get(awayTeam, (None, None))[1],
            "draw_odds": drawEntry[0] if drawEntry else None,
            "draw_bookie": drawEntry[1] if drawEntry else None,
        })

    return structured