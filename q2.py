import json
q=json.load(open("data/needs_check.json"))["items"]
for i in q:
    if i["tier"] in (1,3) and not i["size_m2"] and not i["price"]:
        print(i["agent"], "|", i["street"][:56], "|", i["url"][:70])
