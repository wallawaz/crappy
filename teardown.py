try:
    import hirlite
except Exception as e:
    print e

r = hirlite.Rlite("crappy.rld")
r.command("del", "game:id.1")

