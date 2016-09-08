#!/home/mattermost/mattermost_bot/mattermost_bot_env/bin/python
import game
import random

def create_game():
    have_game = False
    try:
        game.Game.load(1)
        have_game = True
    except KeyError:
        pass

    if have_game:
        return

    created_game = game.Game.create()
    for name, bank_roll in game.ADMINS:
        p = game.Player.create(name=name, bank_roll=bank_roll)
        created_game.players.add(name)
        p.save()
    roller = random.choice(list(created_game.players))
    created_game.roller = roller
    created_game.save()

if __name__ == "__main__":
    create_game()
