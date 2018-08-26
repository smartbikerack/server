from flask import Flask, request, jsonify
import pymongo
from time import time, strftime
import datetime

app = Flask(__name__)

myclient = pymongo.MongoClient("mongodb+srv://admin:masteriot@cluster0-yh0hh.gcp.mongodb.net/test?retryWrites=true")
mydb = myclient["smartbikerack"]

@app.route('/')
def hello():
    return "Hello World!"

@app.route('/testMongo')
def testMongo():
    a = 0
    print(myclient.list_database_names())
    parkings = mydb["parking"]
    for x in parkings.find():
        print(x)

    return "Test"

@app.route('/useSpot/<string:parking>')
def useSpot(parking):
    spot = request.args.get('spot')
    user = request.args.get('user')
    query = {"number": int(spot)}
    col = mydb["spot"]
    park = col.find_one(query)
    print("User {} trying to use spot {} on parking {}".format(user, spot, parking))

    if park["occupied"] == False:
        now = datetime.datetime.now()
        dateName = now.strftime("%Y-%m-%d-%H-%M-%S")
        occupied = {"$set" : {"occupied" : True, "occupiedBy": int(user), "occupiedSince": dateName}}
        col.update_one(query,occupied)
    else:
        return jsonify(
            status = "occupied"
            ), 403

    return jsonify(
        status = "ok")

@app.route('/releaseSpot/<string:parking>')
def releaseSpot(parking):
    spot = request.args.get('spot')
    user = request.args.get('user')
    query = {"number": int(spot)}
    col = mydb["spot"]
    park = col.find_one(query)
    print("User {} trying to release spot {} on parking {}".format(user, spot, parking))

    if park["status"] != "ok":
        return jsonify(
                status = "no available"
                ), 403

    if park["occupied"] == True and park["occupiedBy"] == int(user):
        now = datetime.datetime.now()
        dateName = now.strftime("%Y-%m-%d-%H-%M-%S")
        free = {"$set" : {"occupied" : True, "occupiedBy": None, "occupiedSince": None}}
        col.update_one(query, free)
        then = datetime.datetime.strptime(park["occupiedSince"], "%Y-%m-%d-%H-%M-%S")
        timePassed = now - then
        print(str(timePassed.total_seconds()))
        cost = 0.001 * timePassed.total_seconds()
        mydb["uses"].insert_one({"user" : park["occupiedBy"], "start" : park["occupiedSince"],  "end" : dateName, "cost" : cost})
        return jsonify(
            status = "ok",
            cost =  cost)

    return jsonify(
            status = "occupied"
            ), 403

@app.route('/reserveSpot/<int:parking>')
def reserveSpot(parking):
   spots = mydb["spot"]
   for x in spots.find({"parking" : parking}):
       if x["occupied"] == False:
           print(x)
   return "NOT AVAILABLE"

@app.route('/resetSpot/<int:spot>')
def resetSpot(spot):
    query = {"number" : spot}
    col = mydb["spot"]
    #park = col.find_one(query)
    reset = {"$set" : {"occupied" : False, "occupiedBy" : None, "occupiedSince": None}}
    col.update_one(query, reset)
    return "Reset spot {}".format(spot)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000)
