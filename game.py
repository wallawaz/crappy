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
        add_msg = None

        if player_name not in self.players:
            return "@{pn} please join the game to make a bet".format(pn=player_name)

        if extra_bet:
            player = Player.load(player_name)
            player_current_bets = self.minimum_bet + player.extra_bet + extra_bet
            if player_current_bets > player.bank_roll:
                return "{pn} cannot bet {x}, {pn} only has {bank}".format(
                                                pn=player_name,
                                                x=extra_bet,
                                                bank=player.bank_roll)
            else:
                player.extra_bet += extra_bet
                player.save()
                add_msg = "{pn} added {x} to their bet".format(pn=player_name, x=extra_bet)

        def _player_choice(player_name, choice, add_msg=None):
            already_made_that_bet = "{pn} already made a {bet} bet"
            first_bet = "{pn} made the first {bet} bet"
            choices = {
                "!p": "*pass*",
                "!d": "*do not pass*",
            }
            bet = choices[choice]
            if bet == "*pass*":
                bet_in = self.player_passes
                cannot_bet_in = self.player_do_not_passes
            if bet == "*do not pass*":
                bet_in = self.player_do_not_passes
                cannot_bet_in = self.player_passes

            if player_name not in cannot_bet_in:

                if player_name in bet_in and not extra_bet:
                    return already_made_that_bet.format(pn=player_name, bet=bet)

                if len(bet_in) == 0:
                    msg = first_bet.format(pn=player_name, bet=bet)
                else:
                    other_bets = [ b for b in list(bet_in) if b != player_name ]
                    if len(other_bets) == 0:
                        msg = ""
                    elif len(other_bets) == 1:
                        msg = "{pn} joined {m} in making a {bet} bet".format(
                                                                    pn=player_name,
                                                                    m=other_bets[0],
                                                                    bet=bet)
                    else:
                        msg = "{pn} joined ({m}) in making a {bet} bet".format(pn=player_name,
                                                                                m=",".join(other_bets),
                                                                                bet=bet)
                if bet == "*pass*":
                    self.player_passes.add(player_name)
                if bet == "*do not pass*":
                    self.player_do_not_passes.add(player_name)

                if add_msg and msg:
                    msg += "\n" + "and " + add_msg
                if add_msg and not msg:
                    msg = add_msg
                return msg

            else:
                return "{pn} already chose {bet}".format(pn=player_name,
                                                         bet=bet)

        return _player_choice(player_name, choice, add_msg=add_msg)

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
        crap_message = u"\n {}".format(OUTCOMES["CRAPPED"])
        crap_message += u"\n"
        crap_message += self.reset_game(new_roller=True)
        return crap_message

    def rolled_point(self):
        point_message = u"\n {}".format(OUTCOMES["WIN"])
        point_message += u"\n"
        point_message += self.reset_game(new_roller=False)
        return point_message

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

            if true_pass == False:
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
            if ret:
                full_reply += ret + "\n"

        return full_reply


    def first_roll(self, debug_roll=None):
        reply = u""

        if self.rolls == 0:
            if not debug_roll:
                roll = Roll()
            else:
                roll = debug_roll
            self.rolls += 1
            reply += str(roll).decode("utf8")

            if roll.point in PASS:
                reply += self.winners_losers()
                reply += self.reset_game()

            elif roll.point in DO_NOT_PASS:
                reply += self.winners_losers(true_pass=False)
                reply += self.reset_game(new_roller=True)

            else:
                self.game_point = int(roll.point)
                reply += u"\nPOINT SET"

            self.save()
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
