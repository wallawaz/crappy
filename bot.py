# -*- coding: utf-8 -*-
import game
import requests

from flask import Flask, request, json, g
from constants import BOT_USERNAME, BOT_IMAGE, MATTERMOST_INCOMING, ENDPOINTS

def create_app():
    app = Flask(__name__)

    def payload(message):
        payload = {
            "text": message,
            "username": BOT_USERNAME,
            "icon_url": BOT_IMAGE,
        }
        try:
            r = requests.post(MATTERMOST_INCOMING,
                          headers={"Content-Type":"application/json"},
                          data=json.dumps(payload),
                          params="payload")
            content = r.content
        except Exception as e:
            return e
        return content

    @app.before_request
    def check_token():
        try:
            path = str(request.path)
            tokens = ENDPOINTS[path]
        except Exception as e:
            auth = False
        form = request.form
        auth = str(form["token"]) in tokens
        g.auth = auth
        g.user_name = str(form["user_name"])
        # used for /action post
        g.action = str(form["trigger_word"])
        g.text = str(form["text"])

        g.is_admin = False
        admins = [ admin_name for admin_name, admin_bank_roll in game.ADMINS ]
        if g.user_name in admins:
            g.is_admin = True


    @app.route("/reset", methods=["POST"])
    def reset():
        if g.auth:
            if g.is_admin:
                try:
                    current_game = game.Game.load(1)
                except KeyError:
                    print "NEW GAME"
                    game.create_game()
                    current_game = game.Game.load(1)

                new_roller = current_game.reset_game(new_roller=True)
                send = payload(new_roller)
                current_game.save()
                print send
                if send == "ok":
                    return "reset the game"
                return "derp"

    def find_extra_bet(text):
        words = text.split()
        amount = None
        for word in words:
            try:
                amount = int(word)
            except ValueError:
                pass
            if amount:
                return amount

        return 0


    @app.route("/action", methods=["POST"])
    def player_action():
        if g.auth:
            current_game = game.Game.load(1)
            game_action = None
            player_name = str(g.user_name)

            if g.action == "!p":
                extra_bet = find_extra_bet(g.text)

                game_action = current_game.player_choice(player_name, g.action, extra_bet=extra_bet)
                payload(game_action)

            elif g.action == "!d":
                extra_bet = find_extra_bet(g.text)

                game_action = current_game.player_choice(player_name, g.action, extra_bet=extra_bet)
                payload(game_action)

            elif g.action == "!join":
                game_action = current_game.add_player(player_name)
                payload(game_action)

            elif g.action == "!leave":
                game_action = current_game.remove_player(player_name)
                payload(game_action)

            elif g.action == "!stats":
                player = None
                try:
                    player = game.Player.load(player_name)
                except Exception as e:
                    print e
                if player is not None:
                    active_bets = "active bets: "
                    current_game = game.Game.load(1)
                    if player_name in current_game.player_passes:
                        active_bets += "*pass*"
                    if player_name in current_game.player_do_not_passes:
                        active_bets += "*do_not_pass*"


                    if player.extra_bet is not None and player.extra_bet > 0:
                        active_bets += "\n+$%s" % player.extra_bet

                    player_stats = str(player)
                    player_stats += " " + active_bets
                    payload(player_stats)
                    game_action = player_stats

            elif g.action == "!game":
                current_game_stats = str(current_game)
                payload(current_game_stats)
                game_action = current_game_stats
            elif g.action == "!help":
                messages = (
                    "*commands:*",
                    "`!join` -> join the game",
                    "`!leave` -> leave the game",
                    "`!stats` -> your current stats (bankroll)",
                    "`!game` -> view current game info",
                    "`!p` -> place a *pass bet*",
                    "`!d` -> place a *do not pass bet*",
                    "`!roll` -> roll the dice. will only be accepted if you are the game's roller",
                )
                messages = "\n".join(messages)
                payload(messages)
                game_action = messages
            else:
                pass

            saving_actions = ("!p", "!d", "!join", "!leave")
            if g.action in saving_actions and game_action:
                #XXX
                #current_game.save()
                return game_action
            else:
                return "game not saved"

    @app.route("/roll", methods=["POST"])
    def roll_dice():
        ret = "nothing"
        if g.auth:
            current_game = game.Game.load(1)
            roller = current_game.roller()
            if str(g.user_name) == str(roller):
                print "valid roller"
                if current_game.rolls == 0:
                    print "first roll"
                    rolled = current_game.first_roll()
                else:
                    rolled = current_game.keep_goin()
                send = payload(rolled)
                current_game.save()
                ret = "valid roll"
        return ret

    return app

