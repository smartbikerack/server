from flask import Flask, request, jsonify
import hashlib
import random
import json
import pymongo
from time import time, strftime
import datetime

app = Flask(__name__)

myclient = pymongo.MongoClient("mongodb+srv://admin:masteriot@cluster0-yh0hh.gcp.mongodb.net/test?retryWrites=true")
mydb = myclient["smartbikerack"]


def verifyUser(userID):
    print(userID)
    query = {"number" : userID}
    user = mydb["users"].find_one(query)
    print(user)
    if user["status"] == "ok" and user["active"] == True:
        return user, True, user["current"]
    else:
        return user, False, user["current"]

def updateUser(current, userID):
    query = {"number" : userID}
    change = {"$set" : {"current": current}}
    mydb["users"].update_one(query, change)
    return True

def updateParking(used, parking):
    query = {"number" : parking}
    parking = mydb["parking"].find_one(query)
    print(parking)
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
   print("wdfg")
   if userStatus == False:
        print("User not valid")
        return {"response" : "This user is not valid. Contact us for more info"}

   if userCurrent == True:
        print("User already using a spot")
        return jsonify(response= "You're already using a spot")



   for x in spots.find({"parking" : parking}):
       print("asdfg")
       if x["occupied"] == False:
           print("sdfgom vbnñl,mnj")
           change = {"$set" : {"occupied": True, "occupiedBy": user, "occupiedSince" : dateName}}
           spots.update_one({"number" : x["number"], "parking" : parking}, change)
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
    spotsMemory = []
    for x in spots:
        spotsMemory.append(x)

    for x in parkings:
        #print(x)
        print("Listing spots for this parking::")
        x["spotArray"] = []
        print(x)
        for y in spotsMemory:
            print(y)
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

@app.route('/getCurrentUse/<int:user>')
def getCurrentUses(user):
    query = {"occupiedBy" : user}
    spot = mydb["spot"].find_one(query, {"_id" : 0})
    print(spot)
    if spot == None:
       return jsonify(response = "No current use")
    return json.dumps(spot, ensure_ascii = False)


@app.route('/logIn/<string:email>/<string:password>')
def logIn(email, password):
    query = {"email" : email}
    user = mydb["users"].find_one(query, {"_id":0})
    if user == None:
        return jsonify(response = "Wrong username or password")
    hash_object = hashlib.sha256((password + "" + user["salt"]).encode())
    hex_dig = hash_object.hexdigest()
    if hex_dig  != user["password"]:
        return jsonify(response = "Wrong username or password")
    returnUser = mydb["users"].find_one(query, {"_id":0, "password": 0, "salt": 0})
    return json.dumps(returnUser, ensure_ascii = False)

@app.route('/signUp/<string:email>/<string:name>/<string:password>')
def signUp(email, name, password):
    query = {"email" : email}
    user = mydb["users"].find_one(query, {"_id": 0})
    if user != None:
        return jsonify(response = "User already exists")
    salt = random.getrandbits(128)
    hash_object = hashlib.sha256((password + "" + str(salt)).encode())
    hex_dig = hash_object.hexdigest()
    lastUser = mydb["users"].find({}, {"number" : 1, "_id" : 0}).sort([["number" , pymongo.DESCENDING]]).limit(1)
    for x in lastUser:
        lastId = x["number"]
    insertUser = {"email" : email, "name" : name, "password" : hex_dig, "salt" : str(salt), "status" : "Pending", "active": False, "current": False, "uuid" : "Pending", "number": lastId + 1}
    mydb["users"].insert_one(insertUser)
    return jsonify(answer = "User added without errors")

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000)
