import json
q=json.load(open("data/needs_check.json"))
print(q["tiers"], q["todo"])
for i in q["items"][:6]:
    print(i["tier"], "|", i["street"][:48], "|", i["resort"], "|", i["district"], "|", i["guess_quality"])
