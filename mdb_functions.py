# mostly a scratchwork file to test out functions I will be using to manage thread posts
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId

client = MongoClient("mongodb://stallapp:stall123@cluster0-shard-00-00.bjwrh.mongodb.net:27017,cluster0-shard-00-01.bjwrh.mongodb.net:27017,cluster0-shard-00-02.bjwrh.mongodb.net:27017/stall?ssl=true&replicaSet=Cluster0-shard-0&authSource=admin&retryWrites=true&w=majority")
db = client['stall']

thread = db.threads.find_one({'_id':ObjectId('5fc5d70bf77aba1c5ffe5d6e')})

def nested_return(thread, nested_field, id_field, id, return_field):
    for x in thread[nested_field]:
        if x[id_field] == id:
            return x

# mongo.db.threads.update_one({"_id":ObjectId(id), "thread":{ "$elemMatch": {"postNum":reply}}},{ '$set':{ "thread.$.message":}})

# def postReplacement(thread, nested_field, id_field, id):
#     for x in thread[nested_field]:
#         if x[id_field] == id:
#             return x



post = nestedReturn(thread, 'thread', 'postNum', 2, 'message')
print(post['message'])
print(post['user'])
print(db.threads)



def post_replacement(thread, nested_field, id_field, id, return_field):
    for x in thread[nested_field]:
        if x[id_field] == id:
            return x
