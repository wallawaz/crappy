# -*- coding: utf-8 -*-

from bot import create_app
from tearup import create_game

application = create_app()

if __name__ == "__main__":
    create_game()
    application.run(host="0.0.0.0")
