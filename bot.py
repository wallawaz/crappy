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
        return 1

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

    @app.route("/reset", methods=["POST"])
    def reset():
        if g.auth:
            # check if reset command was issued by admin
            admins = [ admin_name for admin_name, admin_bank_roll in game.ADMINS ]
            if g.user_name in admins:
                try:
                    current_game = game.Game.load(1)
                except KeyError:
                    game.create_game()
                    current_game = game.Game.load(1)

                new_roller = current_game.reset_game(crapped=True)
                send = payload(new_roller)
                current_game.save()
                print send
                if send == 1:
                    return "reset the game"

    @app.route("/join", methods=["POST"])
    def player_join():
        if g.auth:
            current_game = game.Game.load(1)
            current_game.add_player(g.user_name)
            current_game.save()


    @app.route("/action", methods=["POST"])
    def player_action():
        if g.auth:
            current_game = game.Game.load(1)
            game_action = 0
            if g.action == "#p":
                game_action = current_game.player_choice(g.user_name, g.action)
            elif g.action == "#d":
                game_action = current_game.player_choice(g.user_name, g.action)
            elif g.action == "#join":
                game_action = current_game.add_player(g.user_name)
            elif g.action == "#leave":
                game_action = current_game.remove_player(g.user_name)
            elif g.action == "#stats":
                player = None
                try:
                    player = game.Player.load(g.user_name)
                except Exception as e:
                    print e
                if player is not None:
                    player_stats = str(player)
                    send = payload(player_stats)
            else:
                pass
            if game_action > 0:
                current_game.save()

    @app.route("/roll", methods=["POST"])
    def roll_dice():
        if g.auth:
            current_game = game.Game.load(1)
            if g.user_name == str(current_game.roller):
                if current_game.come_in:
                    rolled = current_game.first_roll()
                else:
                    rolled = current_game.keep_goin()
                current_game.save()
                send = payload(rolled)
                if send == 1:
                    print "valid roll"

    return app

