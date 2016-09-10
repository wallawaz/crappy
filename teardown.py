#!/home/mattermost/mattermost_bot/mattermost_bot_env/bin/python
import game
import sys


def tear_down():
    try:
        current_game = game.Game.load(1)
        for i in range(len(current_game.players)):
            del current_game.players[i]
        current_game.delete()
    except KeyError:
        pass

    all_players = game.Player.all()
    for p in all_players:
        p.delete()

if __name__ == "__main__":
    tear_down()
