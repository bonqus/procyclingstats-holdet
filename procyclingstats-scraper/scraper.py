import requests
import random
import re
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import pandas as pd
import numpy as np
import time
from tqdm import tqdm

headers = {"User-agent": "Mozilla/5.0"}
PCS_url = "https://www.procyclingstats.com/"

games = 663
tournaments = 443

def reorder_name(name):
    names = name.split(" ")
    for i in range(len(names)):
        if not names[i].isupper():
            return " ".join(names[i:]) + " " + " ".join(names[:i])
    return name

from name_disrepency_map import disrepency_helper

def _fetch_holdet(rounds):
    t_url = f"https://api.holdet.dk/tournaments/{tournaments}\
    ?appid=holdet&culture=da-DK"
    response = requests.get(t_url).json()
    names = response.get("persons")  # array of people
    players = response.get("players")

    # player id og pris
    g_url = f"https://api.holdet.dk/games/{games}/rounds/{rounds}\
    /statistics?appid=holdet&culture=da-DK"
    prices = requests.get(g_url).json()

    holdet_price = []
    for player in players:

        def pricefilter(x):
            return x["player"]["id"] == player["id"]

        def namefilter(x):
            return (
                x["id"] == player["person"]["id"]
                and player["active"]
                and not player["eliminated"]
            )

        # filfun = lambda x: x["player"]["id"] == player["id"]
        price = list(filter(pricefilter, prices))
        name = list(filter(namefilter, names))
        if len(price) > 0 and len(name) > 0:
            value = price[0]["values"]["value"]
            first = name[0]["firstname"]
            last = name[0]["lastname"]
            # full_name_pro = f"{last} {first}"
            full_name_holdet = f"{first} {last}"
            if full_name_holdet in disrepency_helper:
                # print(disrepency_helper[full_name_holdet])
                full_name_holdet = disrepency_helper[full_name_holdet]
                full_name_holdet = reorder_name(full_name_holdet)
            obj = {
                "Name": full_name_holdet,
                "Price": value,
            }
            holdet_price.append(obj)
    df = pd.DataFrame.from_records(holdet_price)
    return df


def str2int(s: str) -> int or np.nan:
    """Parse a string to an int or np.nan.

    :param s: string
    :returns: int or np.nan

    """
    try:
        return int(s)
    except ValueError:
        return np.nan


def get_rider_urls(race_url: str, year: int) -> list[str]:
    startlist_url = PCS_url + "race/" + race_url + "/" + str(year) + "/startlist"
    response = requests.get(startlist_url, headers=headers)
    page = response.text
    soup = BeautifulSoup(page, "lxml")
    startlist = soup.find_all("a", class_="blue")
    urls = [x["href"] for x in startlist]
    urls = ["https://www.procyclingstats.com/" + u for u in urls]
    return urls


# def get_rider_seasons(rider_url: str) -> list[str]:
#     """Get rider seasons.

#     :param rider_url: primoz-roglic
#     :returns: A list of seasons

#     """
#     response = requests.get(rider_url, headers=headers)
#     page = response.text
#     soup = BeautifulSoup(page, "lxml")
#     seasons = [year.text for year in soup.find("ul", class_="rdrSeasonNav").contents]
#     seasons = seasons[:5]  # grab 5 latest seasons
#     for year in seasons:
#         season_url = rider_url + "&season=" + year
#         response = requests.get(season_url, headers=headers)
#         page = response.text
#         soup = BeautifulSoup(page, "lxml")
#         infolist = soup.find("ul", class_="infolist")
#         urls = [x["href"] for x in startlist]


def get_rider_results(rider_url: str) -> pd.DataFrame:
    """Get 100 last reusult of the rider.

    :param rider_url: The rider_url
    :returns: A DataFrame

    """
    rider_slug = rider_url.split("/")[-1]
    params = {
        "xseason": "",
        "zxseason": "",
        "pxseason": "equal",
        "sort": "date",
        "race": "",
        "km1": "",
        "zkm1": "",
        "pkm1": "equal",
        "limit": "100",
        "offset": "0",
        "topx": "",
        "ztopx": "",
        "ptopx": "smallerorequal",
        "type": "",
        "znation": "",
        "continent": "",
        "pnts": "",
        "zpnts": "",
        "ppnts": "equal",
        "level": "",
        "rnk": "",
        "zrnk": "",
        "prnk": "equal",
        "exclude_tt": "0",
        "racedate": "",
        "zracedate": "",
        "pracedate": "equal",
        "name": "",
        "pname": "contains",
        "category": "",
        "profile_score": "",
        "zprofile_score": "",
        "pprofile_score": "largerorequal",
        "filter": "Filter",
        "id": rider_slug,
        "p": "results",
    }
    url_params = urlencode(params)
    result_url = PCS_url + "rider.php?" + url_params
    response = requests.get(result_url, headers=headers)
    page = response.text
    soup = BeautifulSoup(page, "lxml")
    name = soup.find("h1").text.strip()
    name = re.sub(" +", " ", name)
    team = soup.find("span", class_="red hideIfMobile").text.strip()
    table = soup.find("table", class_="basic")

    record = []
    for row in table.tbody.find_all("tr")[:-1]:  # skip last sum row
        columns = row.find_all("td")
        if len(columns) == 8:
            date = columns[1].text.strip()
            result = str2int(columns[2].text.strip())
            race = columns[3].text.strip()
            race_url = columns[3].find("a")["href"]
            clas = columns[4].text.strip()
            kms = columns[5].text.strip()
            pcs = columns[6].text.strip()
            uci = columns[7].text.strip()
            data = {
                "Name": name,
                "Slug": rider_slug,
                "Team": team,
                "Date": date,
                "Result": result,
                "Race": race,
                "Race_url": race_url,
                "Class": clas,
                "Kms": kms,
                "PCS points": pcs,
                "UCI points": uci,
            }
            record.append(data)

    df = pd.DataFrame.from_records(record)
    return df


def top_n_finish(df: pd.DataFrame, n: int = 15) -> int:
    """How many top n finishes.

    :param df: DataFrame
    :param n: Top n finishes
    :returns: Number of top n finishes

    """
    return len(df[df["Result"] <= n])


def get_races_info(race_urls: list[str]):
    """Get race info.

    :param race_urls: race urls
    :returns: Data frame

    """
    dfs = []
    for race_url in tqdm(race_urls):
        url = PCS_url + race_url
        response = requests.get(url, headers=headers)
        page = response.text
        soup = BeautifulSoup(page, "lxml")
        infolist = soup.find("ul", class_="infolist")
        info = [x.find_all("div")[1].text.strip() for x in infolist.find_all("li")]
        data = {
            "Race_url": race_url,
            "Date": info[0],
            "Start Time": info[1],
            "Avg. speed winner": info[2],
            "Race category": info[3],
            "Distance": info[4],
            "Point scale": info[5],
            # "UCI scale" 6
            "Parcours type": info[6],
            "ProfileScore": info[7],
            "Vert. meters": info[8],
            "Departure": info[9],
            "Arrival": info[10],
            "Race ranking": info[11],
            "Startlist quality score": info[12],
            "Won how": info[13],
            # "Avg. temperature" 15
        }
        dfs.append(data)
        random_wait = 2 * random.random()
        time.sleep(random_wait)
    df = pd.DataFrame.from_records(dfs)
    return df


# TODO: show progress bar
# Parametarize the whole thing for terminal
if __name__ == "__main__":
    # RACE URL for pro cycling stats
    # race_url = "vuelta-a-espana"
    race_url = "giro-d-italia"
    year = 2023
    rider_urls = get_rider_urls(race_url, year)
    dfs = []
    for rider_url in tqdm(rider_urls):
        df = get_rider_results(rider_url)
        random_wait = 2 * random.random()
        time.sleep(random_wait)
        dfs.append(df)
    df = pd.concat(dfs)
    pd.to_pickle(df, "./results.pkl")
    # df = pd.read_pickle("./results.pkl")

    holdet = _fetch_holdet(1)
    df = pd.merge(
        df,
        holdet,
        left_on=df["Name"].str.lower(),
        right_on=holdet["Name"].str.lower(),
        how="left",
    )

    # Get all unique stage urls
    races = df["Race_url"].unique()
    mask = [
        (
            "stage" in race
            and "-kom" != race[-4:]
            and "-points" != race[-7:]
            and "-youth" != race[-6:]
        )
        or "result" in race
        for race in races
    ]
    race_urls = races[mask]
    df_races = get_races_info(race_urls)
    pd.to_pickle(df_races, "./races.pkl")
    # df_races = pd.read_pickle("./races.pkl")

    # kill the key_0 column
    df.drop('key_0', inplace=True, axis=1)

    # merge race info
    df = pd.merge(
        df,
        df_races,
        left_on=df["Race_url"],
        right_on=df_races["Race_url"],
        how="left",
    )

    df_top = df[df["Result"] <= 15]
    # print(df_top.groupby(["Name"])["Result"].count().sort_values(ascending=False))
    # with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
    #     print(df)
    df_group = df_top.groupby(["Slug", "Team", "Price"])["Result"].count()
