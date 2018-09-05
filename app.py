from flask import Flask, request, jsonify
import json
import pymongo
from time import time, strftime
import datetime

app = Flask(__name__)

myclient = pymongo.MongoClient("mongodb+srv://admin:masteriot@cluster0-yh0hh.gcp.mongodb.net/test?retryWrites=true")
mydb = myclient["smartbikerack"]


def verifyUser(userID):
    query = {"number" : userID}
    user = mydb["users"].find_one(query)
    print(user)
    if user["status"] == "ok" and user["active"] == True:
        return user, True, user["current"]
    else:
        return {"user" :  "False"}, False

def updateUser(current, userID):
    query = {"number" : userID}
    change = {"$set" : {"current": current}}
    mydb["users"].update_one(query, change)
    return True

def updateParking(used, parking):
    query = {"number" : parking}
    parking = mydb["parking"].find_one(query)
    spotsUsed = parking["spotsOccupied"]
    if used:
        spotsUsed+=1
    else:
        spotsUsed-=1
    print(spotsUsed)
    if (0 <= spotsUsed) and (spotsUsed <= parking["spots"]):
        change = {"$set" : {"spotsOccupied" :  spotsUsed}}
        mydb["parking"].update_one(query, change)
        return True
    else:
        return False

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


@app.route('/reserveSpot/<int:user>/<int:parking>')
def reserveSpot(user, parking):
   now = datetime.datetime.now()
   dateName = now.strftime("%Y-%m-%d-%H-%M-%S")
   spots = mydb["spot"]
   userNumber, userStatus, userCurrent = verifyUser(user)
   if userStatus == False:
        print("User not valid")
        return {"response" : "This user is not valid. Contact us for more info"}

   if userCurrent == True:
        print("User already using a spot")
        return jsonify(response= "You're already using a spot")



   for x in spots.find({"parking" : parking}):
       if x["occupied"] == False:
           change = {"$set" : {"occupied": True, "occupiedBy": user, "occupiedSince" : dateName}}
           spots.update_one({"number" : x["number"]}, change)
           updateUser(True, user)
           updateParking(True, parking)
           return jsonify(spotReserved =  x["number"], response= "Reserved spot {}".format(x["number"]))

   return jsonify(response= "No spots available")


@app.route('/releaseSpot/<int:user>')
def releaseSpot(user):
    query = {"occupiedBy" : user}
    userNumber, userStatus, userCurrent = verifyUser(user)
    spot = mydb["spot"].find_one(query)
    print(spot)
    if spot == None:
        return jsonify(response = "User not using any spot")
    if spot["occupied"] == True and spot["occupiedBy"] == userNumber["number"]:
        park = mydb["parking"].find_one({"number": spot["parking"]})
        now = datetime.datetime.now()
        dateName = now.strftime("%Y-%m-%d-%H-%M-%S")
        free = {"$set" : {"occupied" : False, "occupiedBy": None, "occupiedSince": None}}
        mydb["spot"].update_one(query, free)
        then = datetime.datetime.strptime(spot["occupiedSince"], "%Y-%m-%d-%H-%M-%S")
        timePassed = now - then
        print(str(timePassed.total_seconds()))
        cost = 0.001 * timePassed.total_seconds()
        mydb["uses"].insert_one({"user" : spot["occupiedBy"], "start" : spot["occupiedSince"],  "end" : dateName, "cost" : cost, "parking" : park["place"], "duration" : timePassed.total_seconds()})
        updateUser(False, user)
        updateParking(False, spot["parking"])
        print("Spot released")
        return jsonify(response = "Spot released correctly")
    return josnify(response = "Error releasing spot")



@app.route('/resetSpot/<int:spot>')
def resetSpot(spot):
    query = {"number" : spot}
    col = mydb["spot"]
    #park = col.find_one(query)
    reset = {"$set" : {"occupied" : False, "occupiedBy" : None, "occupiedSince": None}}
    col.update_one(query, reset)
    return "Reset spot {}".format(spot)

@app.route('/listSpots/')
def listSpots():
    spots = mydb["spot"].find({},{ "_id": 0, "occupiedSince": 0, "occupiedBy":0})
    parkings = mydb["parking"].find({},{ "_id": 0})
    jsonSpots = []

    for x in parkings:
        #print(x)
        print("Listing spots for this parking::")
        x["spotArray"] = []
        #print(x)
        for y in spots:
            if y["parking"] == x["number"]:
               x["spotArray"].append(y)
        jsonSpots.append(x)

    return json.dumps(jsonSpots, ensure_ascii = False)


@app.route('/getUses/<int:user>')
def getUses(user):
    query = {"user" : user}
    uses = mydb["uses"].find(query, {"_id":0})
    jsonUses = []

    for x in uses:
        jsonUses.append(x)
    print(jsonUses)
    return json.dumps(jsonUses, ensure_ascii = False)


if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000)
