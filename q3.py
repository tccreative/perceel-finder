import json
q=json.load(open("data/needs_check.json"))["items"]
t2=[i for i in q if i["tier"]==2]
print(len(t2))
for i in t2[:40]:
    print(i["street"][:52], "||", i["resort"], "||", i["district"])
