# Sports Betting Arbitrage Project  

## Project Overview

## external resource 

### Api odds 
* https://the-odds-api.com/ free version

## Repository Sturucture 

- 'data/cleaned/' -> cleaned datasets used by the team
- 'docs/' -> supporting documentation
- 'notebooks/' -> example notebooks
- 'main.py' -> current project script

## Data preprocessing 
- datasets collected from kaggle
Focus on identifying kaggle datasets that actually fit the popsal and then producing usable clean data

### What was done 
- reviewed multiple downloaded Kaggle datasets related to sports betting, football, tennis, UFC, and soccer
- identified the football odds datasets as the strongest fit for the proposal
- cleaned and standardised the main football betting data
- cleaned all CSV files for related datasets found on kaggle
- created derived arbitrage-ready fields in the main football dataset
- documented the preprocessing process for team use

### Main preprocessing result 
The most important preprocessing output is: 
- 'cleaned_closing_odds.csv'


## Main cleaned Datasets 
which was cleaned as: 
- 'cleaned_closing_odds.csv'

### `cleaned_closing_odds.csv`
**Purpose:** Main dataset for rule-based arbitrage detection and ML feature generation.  
**Stored in:** `data/cleaned/` or shared Drive if too large.  
**Key cleaning changes:** Added `actual_outcome`, implied probability fields, `implied_sum_max`, and `arbitrage_flag`.

### `cleaned_odds_series.csv`
**Purpose:** Support dataset for time-series odds movement and arbitrage persistence analysis.  
**Stored in:** shared Drive due to size.  
**Key cleaning changes:** Standardised column names and preserved bookmaker time-series structure.

### `cleaned_odds_series_b.csv`
**Purpose:** Secondary support dataset for time-series comparison and additional match coverage.  
**Stored in:** shared Drive due to size.  
**Key cleaning changes:** Standardised column names and preserved odds series structure.


### 'cleaned_atp_data.csv'  


### `cleaned_sports_betting_predictive_analysis.csv` 



### `cleaned_ufc_full_data_silver_plus.csv`   

useful for: 
- ufc betting data
- other domain of sport betting data

### `european_soccer_database/database.sqlite`
This is a SQLite database, not a CSV. 

useful for: 
- football team and match metadata
- richer football features later
- possible joins for deeper ML work

## Team Guidance 

Teammate could start here:

1. Use `cleaned_closing_odds.csv` first.
2. Use the `cleaned_odds_series...` files only for persistence or time-based odds analysis.
3. Use the ATP, UFC, and mixed-sport files only if you need comparison datasets or extension ideas.
4. Use `database.sqlite` only when you need deeper football metadata beyond the main betting files.

If you are working on:

- preprocessing -> start with `cleaned_closing_odds.csv`
- ML model selection -> use `cleaned_closing_odds.csv` first, then extend with odds series data if needed
- report writing -> use the markdown and HTML preprocessing notes
- live odds integration -> use historical cleaned football data as the baseline and connect it with the live API later


## How to Access the SQLite Data

The European Soccer Database is stored here:

- `european_soccer_database/database.sqlite`

open it in DB Broswer for SQLite 
