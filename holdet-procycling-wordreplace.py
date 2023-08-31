"""
Cycling stats for Word Replacer II.

Fetch statistics from holdet.dk and export it
as a replace json for the chromeplugin Word Replacer II.
"""
import argparse
import requests
import json

# Tour de France games
# 2019: games=519; tournaments=?
# 2021: games=556; tournaments=?
# 2021: games=589; tournaments=?
# 2022: games=625;  tournaments=419
# 2023: games=663;  tournaments=443

# Vuelta a España games
# 2019: games=527; tournaments=
# 2022: games=635; tournaments=427
# 2023: games=672; tournaments=450

from name_disrepency_map import disrepency_helper


def _fetch(games, tournaments, rounds):
    t_url = f"https://api.holdet.dk/tournaments/{tournaments}\
    ?appid=holdet&culture=da-DK"
    response = requests.get(t_url).json()
    names = response.get("persons")  # array of people
    players = response.get("players")

    # player id og pris
    g_url = f"https://api.holdet.dk/games/{games}/rounds/{rounds}\
    /statistics?appid=holdet&culture=da-DK"
    prices = requests.get(g_url).json()

    rider_replacer = []
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
            value = price[0]["values"]["value"] / 1_000_000
            first = name[0]["firstname"]
            last = name[0]["lastname"]
            full_name_pro = f"{last} {first}"
            full_name_holdet = f"{first} {last}"
            if full_name_holdet in disrepency_helper:
                # print(disrepency_helper[full_name_holdet])
                full_name_pro = disrepency_helper[full_name_holdet]
            obj = {
                "repA": full_name_pro,
                "repB": f"{full_name_holdet}: {value}",
                "type": "Simple",
                "case": "Maintain",
                "active": True,
            }
            rider_replacer.append(obj)

    return json.dumps(rider_replacer, ensure_ascii=False).encode("utf8")


# games = 635
# tournaments = 427
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Holdet replace json.")
    parser.add_argument("game", type=int, help="Game number")
    parser.add_argument("tournament", type=int, help="Tournament number")
    parser.add_argument("round", type=int, help="Spil runde")
    args = parser.parse_args()
    json_string = _fetch(args.game, args.tournament, args.round)

    print(json_string.decode())
    # f = open("replacer.json", "w")
    # f.write(json_string.decode())
    # f.close()
