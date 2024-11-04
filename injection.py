import requests


while True:
    deck_name = input("Enter the name of the deck: ")
    deck_owner = input("Enter the name of the deck owner: ")
    commanders = input("Enter the commanders of the deck separated by ;")
    commanders = commanders.split(";")
    print(commanders)

    data = {
        "name": deck_name,
        "owner": deck_owner,
        "commanders": commanders
    }

    response = requests.post("http://localhost:8000/api/add_deck", json=data)
    if response.status_code == 200:
        print("Deck added successfully!")
    else:
        print("Failed to add deck. Please try again.")