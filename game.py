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
        0: u"□",
        1: u"⚀",
        2: u"⚁",
        3: u"⚂",
        4: u"⚃",
        5: u"⚄",
        6: u"⚅",
    }

    def __init__(self, number):
        numbers = range(7)
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
        0:   u"□",
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
    def __init__(self, point=None):
        if point is None:
            self.di1 = get_dice_val()
            self.di2 = get_dice_val()
            self.point = self.di1 + self.di2
        else:
            self.di1 = Dice(0)
            self.di2 = Dice(0)
            self.point = point

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
    extra_bet = IntegerField(default=0)

    def __repr__(self):
        return u"%s: Bank$: %d" % (self.name, self.bank_roll)

    def win(self, bet):
        self.bank_roll += bet

    def lose(self, bet):
        self.bank_roll -= bet


class Game(walrus.Model):
    database = db
    id = IntegerField(primary_key=True, default=1)
    players = ListField()
    minimum_bet = IntegerField(default=10)
    game_point = IntegerField(default=0)
    rolling_position = IntegerField(default=1)
    rolls = IntegerField(default=0)
    player_passes = SetField()
    player_do_not_passes = SetField()


    def __str__(self):
        players_str = "*players:* " + ",".join(self.players)
        come_in_str = ""
        if self.rolls < 1:
            come_in_str = "*_COME_IN_*"
        if self.rolls >= 1:
            come_in_str += "\n*game point:* " + str(self.game_point)
        roller_str = "*roller:* " + self.roller()
        player_passes_str = "*pass bets:* " + ",".join(self.player_passes)
        player_do_not_passes_str = "*do not pass bets:* " + ",".join(self.player_do_not_passes)

        ret = [ players_str, come_in_str, roller_str, player_passes_str, player_do_not_passes_str]
        return "\n".join(ret)

    def roller(self):
        return self.players[0]

    def add_player(self, player_name):
        if player_name in self.players:
            return "%s already in the game" % player_name
        try:
            player = Player.load(player_name)
        except KeyError:
            player = Player(name=player_name, extra_bet=0)
            player.save()

        self.players.append(player_name)
        return "%s added to game" % player_name

    def remove_player(self, player_name):

        def redis_pop_element(redis_list, element):
            new_list = list()
            for i in range(len(redis_list)):
                x = redis_list.popleft()
                if x != element:
                    new_list.append(x)

            for i in new_list:
                redis_list.append(i)

        if player_name not in self.players:
            return "%s was not in the game" % player_name

        if player_name == self.roller() and self.game_point is not None \
            and self.game_point > 0:
            return "%s cannot leave the game while an active roller" % player_name

        self.player_passes.remove(player_name)
        self.player_do_not_passes.remove(player_name)
        redis_pop_element(self.players, player_name)

        # remove the Player's extra bets
        player = Player.load(player_name)
        player.extra_bet = 0
        player.save()

        if self.roller() == player_name:
            self.reset_game(new_roller=True, clear_bets=False)
        return "%s removed from the game" % player_name

    def player_choice(self, player_name, choice, extra_bet=None):
        if player_name not in self.players:
            return "@{pn} please join the game to make a bet".format(pn=player_name)

        if choice == "!p":
            bet = "*pass*"
            if player_name not in self.player_do_not_passes:

                if player_name in self.player_passes:
                    if extra_bet:
                        player = Player.load(player_name)
                        player.extra_bet += extra_bet
                        player.save()
                        return "{pn} added {x} to their bet".format(pn=player_name, x=extra_bet)

                    else:
                        return "{pn} already made {bet} bet".format(pn=player_name, bet=bet)

                self.player_passes.add(player_name)

                if len(self.player_passes) == 1:
                    return "{pn} made the first {bet} bet".format(pn=player_name, bet=bet)
                else:
                    pass_members = ",".join(self.player_passes)
                    return "{pn} joined ({m}) in making a {bet} bet".format(pn=player_name, m=pass_members, bet=bet)
            else:
                return "{pn} already chose _do_not_pass_".format(pn=player_name)

        if choice == "!d":
            bet = "*do not pass*"
            if player_name not in self.player_passes:

                if player_name in self.player_do_not_passes:
                    if extra_bet:
                        player = Player.load(player_name)
                        player.extra_bet += extra_bet
                        player.save()
                        return "{pn} added {x} to their bet".format(pn=player_name, x=extra_bet)
                    else:
                        return "{pn} already made {bet} bet".format(pn=player_name, bet=bet)

                self.player_do_not_passes.add(player_name)

                if len(self.player_do_not_passes) == 1:
                    return "{pn} made first {bet} bet".format(pn=player_name, bet=bet)

                else:
                    do_not_pass_members = ",".join(self.do_not_pass_members)
                    return "{pn} joined ({m}) in making a {bet} bet".format(pn=player_name, m=do_not_pass_members, bet=bet)
            else:
                return "{pn} already chose _pass_".format(pn=player_name)

        return "derp"

    def reset_game(self, new_roller=False, clear_bets=True):
        print "RESETTING GAME"
        self.game_point = 0
        self.rolls = 0

        # reset all players
        if clear_bets:
            for p in self.players:
                player = Player.load(p)
                player.extra_bet = 0
                print "__PLAYER__"
                print player
                player.save()

                if p in self.player_passes:
                    self.player_passes.remove(p)
                if p in self.player_do_not_passes:
                    self.player_do_not_passes.remove(p)

        if new_roller:
            last_roller = self.players.popleft()

            print "last roller: %s" % last_roller
            print "players left: %s" % self.players

            # add last roller to end of the list
            self.players.append(last_roller)
            print "players now: %s" % self.players
            new_roller = self.players[0]

            msg = u"{u} is the new roller\n{u} type `!roll` when ready to start a new round.".format(u=new_roller)
            return msg

        return "new round"

    def crapped(self):
        self.reset_game(new_roller=True)
        return u"\n {}".format(OUTCOMES["CRAPPED"])

    def rolled_point(self):
        self.reset_game(new_roller=False)
        return u"\n {}".format(OUTCOMES["WIN"])

    #def player_check(self):
    #    if self.player.bank_roll < self.minimum_bet:
    #        print "Sorry, but you lost all of your monies"
    #        sys.exit(5)

    def winners_losers(self, true_pass=True):
        full_reply = u"\n"

        for player_name in self.players:
            player_name = str(player_name)
            player = Player.load(player_name)
            ret = None
            reply = str(player) + "{operation}" + str(self.minimum_bet)

            if true_pass:
                if player.name in self.player_passes:
                    reply = reply.format(operation="+")
                    if player.extra_bet > 0:
                        player.win(self.minimum_bet + player.extra_bet)
                        ret = reply + " +" + str(player.extra_bet)
                    else:
                        player.win(self.minimum_bet)
                        ret = reply

                if player.name in self.player_do_not_passes:
                    reply = reply.format(operation="-")
                    if player.extra_bet > 0:
                        player.lose(self.minimum_bet + player.extra_bet)
                        ret = reply + " -" + str(player.extra_bet)
                    else:
                        player.lose(self.minimum_bet)
                        ret = reply

            if not true_pass:
                if player.name in self.player_do_not_passes:
                    reply = reply.format(operation="+")
                    if player.extra_bet > 0:
                        player.win(self.minimum_bet + player.extra_bet)
                        ret = reply + " +" + str(player.extra_bet)
                    else:
                        player.win(self.minimum_bet)
                        ret = reply

                if player.name in self.player_passes:
                    reply = reply.format(operation="-")
                    if player.extra_bet > 0:
                        player.lose(self.minimum_bet + player.extra_bet)
                        ret = reply + " -" + str(player.extra_bet)
                    else:
                        player.lose(self.minimum_bet)
                        ret = reply

            # round if over set any extra bets to 0
            player.extra_bet = 0
            player.save()

        return full_reply


    def first_roll(self):
        reply = u""

        if self.rolls == 0:
            roll = Roll()
            self.rolls += 1
            reply += str(roll).decode("utf8")

            if roll.point in PASS:
                reply += self.winners_losers()
                self.save()
                self.reset_game()

            elif roll.point in DO_NOT_PASS:
                reply += self.winners_losers(true_pass=False)
                self.save()
                self.reset_game(new_roller=True)

            else:
                self.game_point = int(roll.point)
                self.save()
                reply += u"\nPOINT SET"
            return reply
        else:
            raise Exception("not first roll")

    def keep_goin(self, debug_roll=None):
        reply = u""
        if not debug_roll:
            roll = Roll()
        else:
            roll = debug_roll
        self.rolls += 1
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

def create_game():
    game = Game.create()
    for name, bank_roll in ADMINS:
        p = Player.create(name=name, bank_roll=bank_roll, extra_bet=0)
        game.players.add(name)
        p.save()
    roller = self.players[0]
    game.roller = roller
    game.save()

def clear_games():
    pass
