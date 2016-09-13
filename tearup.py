import game
import sys

def create_game():
    created_game = game.Game.create(rolls=0)
    for name, bank_roll in game.ADMINS:
        p = game.Player.create(name=name, bank_roll=bank_roll, extra_bet=0)
        created_game.players.append(name)
        p.save()
    created_game.save()

def delete_game(i):
    i = int(i)
    gx = game.Game.load(i)
    gx.delete()

if __name__ == "__main__":
    for arg in sys.argv:
        print arg
        if "del" in arg:
            delete_game(1)
            break
    create_game()
