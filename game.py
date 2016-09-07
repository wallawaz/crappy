# -*- coding: utf8 -*-
import random
import sys
import walrus
from walrus.tusks.rlite import WalrusLite
from walrus import TextField, IntegerField, ListField, SetField, BooleanField

db = WalrusLite("crappy.rld")

PASS = (7,11)
DO_NOT_PASS = (2,3,12)
ADMINS = [("bwall",100)]

OUTCOMES = {
    "CRAPPED": u"💩",
    "WIN": u"💰",
    }

class Dice(object):
    di = {
        1: u"⚀",
        2: u"⚁",
        3: u"⚂",
        4: u"⚃",
        5: u"⚄",
        6: u"⚅",
    }

    def __init__(self, number):
        numbers = range(1,7)
        if number in numbers:
            self.number = number
        else:
            self.number = None

    def __add__(self, d):
        return self.number + d.number

    def __repr__(self):
        return self.di[self.number].encode("utf8")

    def get_pic(self):
        return self.di[self.number]

def get_dice_val():
    choices = range(1,7)
    return Dice(random.choice(choices))

NUMBERS = {
        1:   u"❶",
        2:   u"❷",
        3:   u"❸",
        4:   u"❹",
        5:   u"❺",
        6:   u"❻",
        7:   u"❼",
        8:   u"❽",
        9:   u"❾",
        10:  u"❿",
        11:  u"❶" + u"❶",
        12:  u"❶" + u"❷",
    }


class Roll(object):
    def __init__(self):
        self.di1 = get_dice_val()
        self.di2 = get_dice_val()
        self.point = self.di1 + self.di2

    def __repr__(self):
        x = str(self.di1).decode("utf8")
        x += u"\t"
        x += str(self.di2).decode("utf8")
        x += u"\t"
        x += NUMBERS[self.point]
        return x.encode("utf8")

    def __str__(self):
        x = str(self.di1).decode("utf8")
        x += u"\t"
        x += str(self.di2).decode("utf8")
        x += u"\t"
        x += NUMBERS[self.point]
        return x.encode("utf8")


class Player(walrus.Model):
    database = db
    name = TextField(primary_key=True)
    bank_roll = IntegerField(default=100)

    def __repr__(self):
        return u"%s: $%d" % (self.name, self.bank_roll)

    def win(self, bet):
        self.bank_roll += bet

    def lose(self, bet):
        self.bank_roll -= bet


class Game(walrus.Model):
    database = db
    id = IntegerField(primary_key=True, default=1)
    players = SetField()
    minimum_bet = IntegerField(default=10)
    come_in = BooleanField(default=True)
    #roll = TextField()
    game_point = IntegerField(default=0)
    roller = TextField()
    player_passes = SetField()
    player_do_not_passes = SetField()

    def __str__(self):
        players_str = "*players:* " + ",".join(self.players)
        come_in_str = "*come in roll:* " + str(self.come_in)
        if not self.come_in:
            come_in_str += "\n*game point:* " + str(self.game_point)
        roller_str = "*roller:* " + self.roller
        player_passes_str = "*pass bets:* " + ",".join(self.player_passes)
        player_do_not_passes_str = "*do not pass bets:* " + ",".join(self.player_do_not_passes)

        ret = [ players_str, come_in_str, roller_str, player_passes_str, player_do_not_passes_str]
        return "\n".join(ret)

    def add_player(self, player_name):
        if player_name in self.players:
            return "%s already in the game" % player_name
        try:
            player = Player.load(player_name)
        except KeyError:
            player = Player(name=player_name)

        self.players.add(player_name)
        self.players.save()
        return "%s added to game" % player_name

    def remove_player(self, player_name):
        if player_name not in self.players:
            return "%s was not in the game" % player_name
        self.players.remove(player_name)
        self.players.save()
        return "%s removed from the game" % player_name

    def player_choice(self, player_name, choice):
        if player_name not in self.players:
            return "@{pn} please join the game to make a bet".format(pn=player_name)
        if choice == "!p":
            if player_name not in self.player_do_not_passes:
                self.player_passes.add(player_name)
                return 1
            return "{pn} already chose _DO_NOT_PASS_".format(pn=player_name)

        if choice == "!d":
            if player_name not in self.player_passes:
                self.player_do_not_passes.add(player_name)
                return -1
            return "{pn} already chose _PASS_".format(pn=player_name)
        return "derp"

    def reset_game(self, new_roller=False):
        self.come_in = True
        self.roll = None
        self.game_point = 0

        # reset all players
        pp = list(self.player_passes.members())
        for p in pp:
            self.player_passes.remove(p)
        pdnp = list(self.player_do_not_passes.members())
        for p in pdnp:
            self.player_do_not_passes.remove(p)

        if new_roller:
            new_roller_message = self.get_new_roller()
            return new_roller_message

    def get_new_roller(self):
        player = random.choice(list(self.players))
        self.roller = player
        msg = u"@{u} is the new roller\n@{u} Type !roll when ready to start a new round.".format(u=self.roller)
        return msg

    def choices(self):
        msg = u""
        for p in self.players:
            msg += str(p).encode("utf8")
            msg += u"\n"

        msg += u"Before the next roll enter:\n`!p` for PASS\n`!d` for DO NOT PASS"
        return msg

    def crapped(self):
        self.reset_game(crapped=True)
        return u"\n {}".format(OUTCOMES["CRAPPED"])

    def rolled_point(self):
        self.reset_game(crapped=False)
        return u"\n {}".format(OUTCOMES["WIN"])

    #def player_check(self):
    #    if self.player.bank_roll < self.minimum_bet:
    #        print "Sorry, but you lost all of your monies"
    #        sys.exit(5)

    def winners_losers(self, true_pass=True):
        reply = u"\n"

        for player_name in self.players:
            player_name = str(player_name)
            player = Player.load(player_name)
            reply += str(player) + ' ^ ' + str(self.minimum_bet)

            if true_pass:
                if player.name in self.player_passes:
                    player.win(self.minimum_bet)
                    reply = reply.replace(u"^",u"+")
                if player.name in self.player_do_not_passes:
                    player.lose(self.minimum_bet)
                    reply = reply.replace(u"^",u"-")

            if not true_pass:
                if player.name in self.player_do_not_passes:
                    player.win(self.minimum_bet)
                    reply = reply.replace(u"^",u"+")

                if player.name in self.player_passes:
                    player.lose(self.minimum_bet)
                    reply = reply.replace(u"^", u"-")
            reply += "\n"
            player.save()

        if not true_pass:
            new_player_message = self.reset_game(new_roller=True)
            reply += new_player_message + "\n"
        return reply


    def first_roll(self):
        reply = u""
        if not self.roller:
            self.get_new_roller()

        if self.come_in:
            roll = Roll()
            reply += str(roll).decode("utf8")
            self.come_in = False

            if roll.point in PASS:
                reply += self.winners_losers()
                self.reset_game()

            elif roll.point in DO_NOT_PASS:
                reply += self.winners_losers(true_pass=False)
                self.reset_game(new_roller=True)

            else:
                self.game_point = int(roll.point)
                self.save()
                reply += u"\nPOINT SET"
            return reply

    def keep_goin(self):
        reply = u""
        roll = Roll()
        reply += str(roll).decode("utf8")

        reply += u"\nROLLING FOR %s" % NUMBERS[self.game_point]

        if roll.point == 7:
            reply += self.winners_losers(true_pass=False)
            reply += self.crapped()
            return reply

        elif roll.point == self.game_point:
            reply += self.winners_losers()
            reply += self.rolled_point()
            return reply
        else:
            return reply

    def who_is_roller(self):
        return u"@{} is currently rolling".format(self.roller)


def create_game():
    game = Game.create()
    for name, bank_roll in ADMINS:
        p = Player.create(name=name, bank_roll=bank_roll)
        game.players.add(name)
        p.save()
    roller = random.choice(list(game.players))
    game.roller = roller
    game.save()

def clear_games():
    pass
