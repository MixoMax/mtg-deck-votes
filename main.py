from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.requests import Request
import uvicorn

import sqlite3
import random
import time
from dataclasses import dataclass

app = FastAPI()


@dataclass
class MTGDeck:
    id: int
    name: str
    owner: str
    commanders: list[str]
    n_matchups_won: int
    n_matchups_lost: int


conn = sqlite3.connect("deck_rankings.db")
c = conn.cursor()

cmd = """
CREATE TABLE IF NOT EXISTS deck_rankings (
    id INTEGER PRIMARY KEY,
    deck_name TEXT,
    deck_owner TEXT,
    deck_commanders TEXT,
    n_matchups_won INTEGER,
    n_matchups_lost INTEGER
);
"""

c.execute(cmd)
conn.commit()


decks: dict[int, MTGDeck] = {} # id -> MTGDeck

cmd = "SELECT * FROM deck_rankings;"
c.execute(cmd)
for row in c.fetchall():
    id, name, owner, commanders, n_matchups_won, n_matchups_lost = row
    decks[id] = MTGDeck(id, name, owner, commanders.split(";"), n_matchups_won, n_matchups_lost)



def deck_to_json(deck: MTGDeck):
    return {
        "id": deck.id,
        "name": deck.name,
        "owner": deck.owner,
        "commanders": deck.commanders,
        "n_matchups_won": deck.n_matchups_won,
        "n_matchups_lost": deck.n_matchups_lost
    }


def create_deck(name: str, owner: str, commanders: list[str]):
    global decks
    new_id = max(decks.keys(), default=0) + 1
    decks[new_id] = MTGDeck(new_id, name, owner, commanders, 0, 0)
    
    cmd = "INSERT INTO deck_rankings (deck_name, deck_owner, deck_commanders, n_matchups_won, n_matchups_lost) VALUES (?, ?, ?, ?, ?);"
    c.execute(cmd, (name, owner, ";".join(commanders), 0, 0))
    conn.commit()


def new_ratings(winner_id: int, loser_id: int):
    global decks
    winner = decks[winner_id]
    loser = decks[loser_id]

    winner.n_matchups_won += 1
    loser.n_matchups_lost += 1

    cmd = "UPDATE deck_rankings SET n_matchups_won = ?, n_matchups_lost = ? WHERE id = ?;"
    c.execute(cmd, (winner.n_matchups_won, winner.n_matchups_lost, winner_id))
    c.execute(cmd, (loser.n_matchups_won, loser.n_matchups_lost, loser_id))

    conn.commit()


def get_decks_sorted():
    global decks
    return sorted(decks.values(), key=lambda x: x.n_matchups_won - x.n_matchups_lost, reverse=True)


def get_decks_for_voting():
    global decks


    votes: dict[int, int] = {}
    for deck in decks.values():
        votes[deck.id] = deck.n_matchups_won + deck.n_matchups_lost

    total = sum(votes.values())

    # weighted so that the decks with fewer votes are more likely to be picked
    weights = [1 - votes[deck.id] / total for deck in decks.values()]

    deck1, deck2 = random.choices(list(decks.keys()), weights=weights, k=2)

    if deck1 == deck2 and len(decks) > 1:
        return get_decks_for_voting()

    return deck1, deck2




@app.get("/", response_class=FileResponse)
async def read_root():
    return FileResponse("index.html")

@app.get("/api/leaderboard")
async def read_leaderboard():
    return JSONResponse(content=[deck_to_json(deck) for deck in get_decks_sorted()])

@app.get("/api/get_new_matchup")
async def read_new_matchup():
    deck1, deck2 = get_decks_for_voting()
    if deck1 is None or deck2 is None:
        return JSONResponse(content={"error": "timeout"})
    return JSONResponse(content={"deck1": deck_to_json(decks[deck1]), "deck2": deck_to_json(decks[deck2])})

@app.get("/api/vote")
async def vote(winner_id: int, loser_id: int):
    new_ratings(winner_id, loser_id)
    return JSONResponse(content={"success": True})

@app.post("/api/add_deck")
async def post_add_deck(request: Request):

    data = await request.json()
    name = data["name"]
    owner = data["owner"]
    commanders = data["commanders"]
    create_deck(name, owner, commanders)
    return JSONResponse(content={"success": True})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)