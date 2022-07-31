import sys
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Pandas Frame printing settings
desired_width = 320
pd.set_option('display.width', desired_width)
pd.set_option('display.max_columns', 16)

# Get values from the command line based on user's league settings
try:
    league_type = str(sys.argv[1])
    league_size = int(sys.argv[2])
    players_per_roster = int(sys.argv[3])

    if league_type not in ['h', 's', 'p']:
        raise Exception('Not a league type')
except ValueError as e:
    quit()

# Dictionary for the three league types
league_types = {
    'h': .5,
    'p': 1,
    's': 0
}

# Scoring values for the various stats recorded
scoring_weights = {
    'receptions': league_types.get(league_type),
    'receiving_yds': 0.1,
    'receiving_td': 6,
    'fumble': -2,
    'rushing_yds': 0.1,
    'rushing_td': 6,
    'passing_yds': 0.04,
    'passing_td': 4,
    'int': -2
}

# Links for scraping Fantasy Pros Projections
projection_links = {
    'qb': 'https://www.fantasypros.com/nfl/projections/qb.php?week=draft',
    'rb': 'https://www.fantasypros.com/nfl/projections/rb.php?week=draft',
    'wr': 'https://www.fantasypros.com/nfl/projections/wr.php?week=draft',
    'te': 'https://www.fantasypros.com/nfl/projections/te.php?week=draft',
}

# Links for ADP values
league_type_adp = {
    'h': 'https://www.fantasypros.com/nfl/adp/half-point-ppr-overall.php',
    'p': 'https://www.fantasypros.com/nfl/adp/ppr-overall.php',
    's': 'https://www.fantasypros.com/nfl/adp/overall.php'
}

# --- Scrape Web for Projections on Fantasy Pros ---
total_projection = pd.DataFrame()

for pos, sites in projection_links.items():
    projection_url = sites
    page = requests.get(projection_url)
    soup = BeautifulSoup(page.content, 'html.parser')
    table = soup.find('table', attrs={'id': 'data'})
    df = pd.read_html(str(table))[0]

    # Variation to the Drop Level to join the upper level of
    df.columns = ['_'.join(col) for col in df.columns]

    # Separate the Player Name and Team and add the Position Column
    df['PLAYER'] = df.iloc[:, 0].apply(lambda x: ' '.join(x.split(' ')[:-1]))
    df['TEAM'] = df.iloc[:, 0].apply(lambda x: x.split(' ')[-1])
    df['POS'] = pos.upper()
    df = df.drop('MISC_FPTS', axis=1)

    # Remove the combined string column of name and team, reorder columns for ease of reading
    df = df.iloc[:, 1:]
    df = df.loc[:, list(df.columns[-3:]) + list(df.columns[:-3])]

    # Concat the looped data frames of varying positions into one overall data frame.
    total_projection = pd.concat([total_projection, df])
    total_projection = total_projection.fillna(0)
# --- END Scrape Web for Projections on Fantasy Pros ---


# --- Add Fantasy Points to the Projection DF based on league type ---
total_projection['FAN_PTS'] = (
    total_projection['PASSING_YDS'] * scoring_weights['passing_yds'] +
    total_projection['PASSING_TDS'] * scoring_weights['passing_td'] +
    total_projection['PASSING_INTS'] * scoring_weights['int'] +
    total_projection['RUSHING_YDS'] * scoring_weights['rushing_yds'] +
    total_projection['RUSHING_TDS'] * scoring_weights['rushing_td'] +
    total_projection['MISC_FL'] * scoring_weights['fumble'] +
    total_projection['RECEIVING_YDS'] * scoring_weights['receiving_yds'] +
    total_projection['RECEIVING_TDS'] * scoring_weights['receiving_td']
)
# --- END Add Fantasy Points to the Projection DF based on league type ---


# --- Scrape For ADP Values ---
adp_url = f'{league_type_adp.get(league_type)}'
page2 = requests.get(adp_url)
soup = BeautifulSoup(page2.content, 'html.parser')
table2 = soup.find('table', attrs={'id': 'data'})
adp_df = pd.read_html(str(table2))[0]

# Split the player name, team from the combined string, remove number from position category
adp_df['PLAYER'] = adp_df['Player Team (Bye)'].apply(lambda x: ' '.join(x.split()[:-2]))
adp_df['TEAM'] = adp_df['Player Team (Bye)'].apply(lambda x: x.split()[-2])
adp_df['POS'] = adp_df['POS'].str[:2]
adp_df = adp_df.loc[:, ['PLAYER', 'TEAM', 'POS', 'AVG', 'Rank']]

# Limit ADP_DF to 101 players to find the replacement players at a limit we set
adp_df_cutoff = adp_df.sort_values(by='Rank')[:101]
# --- END Scrape For ADP Values ---


# --- Merge Projection DataFrame with ADP Cutoff dataframe to find replacement player values for VOR ---
merged_adp = adp_df_cutoff.merge(total_projection.loc[:, ['PLAYER', 'TEAM', 'POS', 'FAN_PTS']],
                                 on=['PLAYER', 'TEAM', 'POS'])

# Loop through the merged adp df to find the last instance of each position and the projected fantasy points associated
replacement_player_values = {}
for i, row in merged_adp.iterrows():
    replacement_player_values[row['POS']] = row['FAN_PTS']
# --- END Merge Projection DataFrame with ADP Cutoff dataframe to find replacement player values for VOR


# --- Add VOR Column to the Total Projection data frame to calculate it for each player. Create VOR Frame
# Filter out players with no position as no to break the VOR calculation
total_projection = total_projection.loc[total_projection['POS'].isin(['QB', 'RB', 'WR', 'TE'])]
total_projection['VOR'] = total_projection.apply(lambda x: x['FAN_PTS']-replacement_player_values.get(x['POS']), axis=1)

# Create a new Data Frame in order for ranking based on VOR
vor_df = total_projection.loc[:, ['PLAYER', 'TEAM', 'POS', 'FAN_PTS', 'VOR']]
vor_df['VOR_Rank'] = vor_df['VOR'].rank(ascending=False)
vor_df = vor_df.sort_values(by='VOR', ascending=False)

# Normalize the VOR values to make them easier to read
vor_df['VOR'] = vor_df['VOR'].apply(lambda x: (x - vor_df['VOR'].min()) / (vor_df['VOR'].max() - vor_df['VOR'].min()))
# --- END Add VOR Column to the Total Projection data frame to calculate it for each player. Create VOR Frame ---


# --- Create The Final Data Frame.  Merge the ADP Data Frame and the VOR frame ---
# Rename columns to not confuse adp rank and vor rank
adp_df = adp_df.rename({
    'AVG': 'AVG_ADP',
    'Rank': 'ADP_Rank'
}, axis=1)

final_df = vor_df.merge(adp_df.loc[:, ['PLAYER', 'TEAM', 'POS', 'ADP_Rank', 'AVG_ADP']], how='left',
                        on=['PLAYER', 'TEAM', 'POS'])

# Fill non available values with 0
final_df = final_df.fillna(0)

# Create new Column for ADP - VOR, how we will determine our sleeper players
final_df['ADP less VOR'] = final_df['ADP_Rank'] - final_df['VOR_Rank']

# Remove Values that would break our calculation
for index, row in final_df.iterrows():
    if row['ADP_Rank'] == 0:
        final_df.drop(index, inplace=True)
# --- END Create The Final Data Frame.  Merge the ADP Data Frame and the VOR frame ---


# --- Print to the user the sleepers! ---
# Take in account league size of user and complete last filter by general league size
roster_bound = (league_size * players_per_roster) + 1
final_df = final_df[:roster_bound]
draft_pool = final_df.sort_values(by='ADP_Rank')

# Loop through the various positions and print the values to the screen
positions = ['QB', 'RB', 'WR', 'TE']
for pos in positions:
    pool = draft_pool.query(
        "POS == @pos"
    )
    print()
    print(pos)
    print(pool.sort_values(by='ADP less VOR', ascending=True)[:6])
# --- END Print to the user the sleepers! ---
