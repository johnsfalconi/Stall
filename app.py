# since I'm a forgetful freddy, here's the process to push to git and heroku
    # 1. $ pip freeze > requirements.txt
    # 2. $ git add .
    # 3. $ git commit -m "<update summary here>"
    # 4. $ git remote -v
    # 5. $ git push heroku master


from flask import Flask, render_template, url_for, request, redirect
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime
from dotenv import load_dotenv  #idk how to use this too well yet
import cloudinary
import cloudinary.uploader
import cloudinary.api
import functools
import hashlib
import random
import re
import os                       #this was added too and idk what to do with it

# load .env file
load_dotenv()

app = Flask(__name__, static_folder="./static/")
app.config['MONGO_DBNAME'] = os.environ.get("MONGO_DBNAME") or os.getenv("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI") or os.getenv("MONGO_URI")
mongo = PyMongo(app)

cloudinary.config(cloud_name = (os.environ.get("CLOUD_NAME") or os.getenv("CLOUD_NAME")), 
    api_key = (os.environ.get("API_KEY") or os.getenv("API_KEY")), 
    api_secret = (os.environ.get("API_SECRET") or os.getenv("API_SECRET")))


def __repr__(self):
    return '<Task %r' % self.id

# Thread creation and index page generation with the list of threads.
@app.route("/", methods = ['POST', 'GET'])
def index():

    if request.method == 'POST':
        input_file = request.files["media"]

        if input_file: 
            content = cloudinary.uploader.upload(input_file)
            pic = cloudinary.CloudinaryImage(content["public_id"])
            media = pic.url
            if int(content["height"]) >= int(content["width"]):
                pic.url_options.update({"height":400})
                media_thumb = pic.url
            else:
                pic.url_options.update({"width":400})
                media_thumb = pic.url
        else:
           media = ""
           media_thumb = ""

        try:
            # this is all stored as a variable so it can be laid out for readability
            new_thread = {
                'title':str(request.form['title']), 
                'board':'Global', 
                'formattedDate':str(datetime.now().strftime("%b. %d, %Y")), 
                'date':datetime.now(),  
                'formattedLastUpdated':datetime.now().strftime("%b. %d, %Y %I:%M%p"), 
                'lastUpdated':datetime.now(), 'posts':1, 
                'threadUsers':[ { 'ip':request.remote_addr, 'userID':'OP', 'idColor':'#ffffff'  } ],
                'thread':[ { 
                    'message':request.form['post'], 
                    'media':media,
                    'mediaThumb':media_thumb,
                    'formattedPosted':datetime.now().strftime("%b. %d, %Y %I:%M%p"), 
                    'postNum':1, 
                    'user':'OP', 
                    'idColor':'#ffffff',
                    'userIP':request.remote_addr, 
                    'replies':[] 
                } ]
            }
            # the actual insert_one statement saved to a variable so the new document's _id can be referenced
            x = mongo.db.threads.insert_one(new_thread)
            
            #redirect using the thread app route to bring the user to the newly-inserted thread
            return redirect('/t/' + str(x.inserted_id))

        except:
            return 'There was an issue adding'
    else:
        threads = list(mongo.db.threads.find({'board':'Global'}))
        return render_template("index.html", threads = threads)


# deleting thread (this should probably only be used for moderators and for the automated system for managing threads)
@app.route('/delete/<id>')
def delete(id):
    try:
        mongo.db.threads.delete_one({"_id":ObjectId(id)})
        return redirect('/')
    except:
        return 'there was a problem deleting'


# working with individual threads
@app.route('/t/<id>', methods = ['GET', 'POST'])
def t(id):
    thread = mongo.db.threads.find_one_or_404({'_id':ObjectId(id)})
    url = request.url
    post_link = re.compile(r'^\[[0-9]+\]')

    if request.method == 'POST':
        # increment post count for the thread document
        new_post_count = thread['posts'] + 1
        message = request.form['message']
        input_file = request.files["media"]

        # getting ip address from the post request
        ip_address = request.remote_addr
        
        # this checks to see if the ip address has posted previously.  If not, a new user ID will be generated and stored
        if mongo.db.threads.find({'_id':ObjectId(id), 'threadUsers.ip':ip_address}).count() == 0:
            color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
            m = hashlib.md5()
            m.update(str(str(thread['_id']) + ip_address).encode('utf-8'))
            userid = str(m.hexdigest())[0:10]
            mongo.db.threads.update_one({'_id':ObjectId(id)},{'$push':{'threadUsers':{'ip':ip_address, 'userID':userid, 'idColor':color}}})
        # if the ip address was used before, this next block finds the corresponding user ID so it can be attached to the post
        else:
            for user in thread['threadUsers']:
                if user['ip'] == ip_address:
                    userid = user['userID']
                    color = user['idColor']

        # the message is then parsed through to find all the post replies
        replies = []

        for line in message.split('\n'):
            if len(line) > 0:
                if line[0] != '>':
                    for word in line.split(' '):
                        if post_link.match(word):
                            if new_post_count != int(word.replace('[', '').replace(']','')):
                                for post in thread['thread']:
                                    if post['postNum'] == int(word.replace('[', '').replace(']','')):
                                        replies.append(post['postNum'])

        for reply in list(set(replies)):
            mongo.db.threads.update_one({"_id":ObjectId(id), "thread":{ "$elemMatch": {"postNum":reply}}},{ '$push':{ "thread.$.replies": {'reply':new_post_count }}})

        # image files that have been attached
        if input_file: 
            content = cloudinary.uploader.upload(input_file)
            pic = cloudinary.CloudinaryImage(content["public_id"])
            media = pic.url
            if int(content["height"]) >= int(content["width"]):
                pic.url_options.update({"height":200})
                media_thumb = pic.url
            else:
                pic.url_options.update({"width":200})
                media_thumb = pic.url
        else:
           media = ""
           media_thumb = ""


        # the post and all its corresponding information is posted to the thread
        thread_update = { '$push':
                            { 'thread':
                                { 'message':message, 
                                'media':media,
                                'mediaThumb':media_thumb,
                                'posted':datetime.now(),
                                'formattedPosted':datetime.now().strftime("%b. %d, %Y %I:%M%p"),  
                                'postNum':new_post_count, 
                                'user':userid, 
                                'idColor':color,
                                'userIP':ip_address, 
                                'replies':[] 
                                }
                            }, 
                            '$set':
                                { 'formattedLastUpdated':datetime.now().strftime("%b. %d, %Y %I:%M%p"), 
                                'lastUpdated':datetime.now(), 
                                'posts':new_post_count
                                }
                            }
        mongo.db.threads.update_one({"_id":ObjectId(id)},thread_update)
        
        # the thread is then refreshed
        try:
            return redirect('/t/' + str(thread['_id']))
        except:
            return 'thread does not exist'
    else:
        thread = mongo.db.threads.find_one_or_404({'_id':ObjectId(id)})
        return render_template('thread.html', thread = thread, link = post_link)



@app.route("/<keyword>/", methods = ['POST', 'GET'])
def boardIndex(keyword):
    if request.method == 'POST':
        input_file = request.files["media"]

        if input_file: 
            content = cloudinary.uploader.upload(input_file)
            pic = cloudinary.CloudinaryImage(content["public_id"])
            media = pic.url
            if int(content["height"]) >= int(content["width"]):
                pic.url_options.update({"height":400})
                media_thumb = pic.url
            else:
                pic.url_options.update({"width":400})
                media_thumb = pic.url
        else:
            media = ""
            media_thumb = ""

        try:
            # this is all stored as a variable so it can be laid out for readability
            new_thread = {
                'title':str(request.form['title']), 
                'board':keyword, 
                'formattedDate':str(datetime.now().strftime("%b. %d, %Y")), 
                'date':datetime.now(),  
                'formattedLastUpdated':datetime.now().strftime("%b. %d, %Y %I:%M%p"), 
                'lastUpdated':datetime.now(), 'posts':1, 
                'threadUsers':[ { 'ip':request.remote_addr, 'userID':'OP', 'idColor':'#ffffff'  } ],
                'thread':[ { 
                    'message':request.form['post'], 
                    'media':media,
                    'mediaThumb':media_thumb,
                    'formattedPosted':datetime.now().strftime("%b. %d, %Y %I:%M%p"), 
                    'postNum':1, 
                    'user':'OP', 
                    'idColor':'#ffffff',
                    'userIP':request.remote_addr, 
                    'replies':[] 
                } ]
            }
            # the actual insert_one statement saved to a variable so the new document's _id can be referenced
            x = mongo.db.threads.insert_one(new_thread)
            
            #redirect using the thread app route to bring the user to the newly-inserted thread
            return redirect('/' + keyword + '/t/' + str(x.inserted_id))

        except:
            return 'There was an issue adding'
    else:
        threads = list(mongo.db.threads.find({'board':keyword}))
        return render_template("index.html", threads = threads, keyword = keyword)


@app.route('/<keyword>/delete/<id>')
def boardDelete(id, keyword):
    try:
        mongo.db.threads.delete_one({"_id":ObjectId(id)})
        return redirect('/' + keyword + '/')
    except:
        return 'there was a problem deleting'



@app.route('/<keyword>/t/<id>', methods = ['GET', 'POST'])
def boardT(keyword, id):
    thread = mongo.db.threads.find_one_or_404({'_id':ObjectId(id)})
    url = request.url
    post_link = re.compile(r'^\[[0-9]+\]')

    if request.method == 'POST':
        # increment post count for the thread document
        new_post_count = thread['posts'] + 1
        message = request.form['message']
        input_file = request.files["media"]

        # getting ip address from the post request
        ip_address = request.remote_addr
        
        # this checks to see if the ip address has posted previously.  If not, a new user ID will be generated and stored
        if mongo.db.threads.find({'_id':ObjectId(id), 'threadUsers.ip':ip_address}).count() == 0:
            color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
            m = hashlib.md5()
            m.update(str(str(thread['_id']) + ip_address).encode('utf-8'))
            userid = str(m.hexdigest())[0:10]
            mongo.db.threads.update_one({'_id':ObjectId(id)},{'$push':{'threadUsers':{'ip':ip_address, 'userID':userid, 'idColor':color}}})
        # if the ip address was used before, this next block finds the corresponding user ID so it can be attached to the post
        else:
            for user in thread['threadUsers']:
                if user['ip'] == ip_address:
                    userid = user['userID']
                    color = user['idColor']

        # the message is then parsed through to find all the post replies
        replies = []

        for line in message.split('\n'):
            if len(line) > 0:
                if line[0] != '>':
                    for word in line.split(' '):
                        if post_link.match(word):
                            if new_post_count != int(word.replace('[', '').replace(']','')):
                                for post in thread['thread']:
                                    if post['postNum'] == int(word.replace('[', '').replace(']','')):
                                        replies.append(post['postNum'])

        for reply in list(set(replies)):
            mongo.db.threads.update_one({"_id":ObjectId(id), "thread":{ "$elemMatch": {"postNum":reply}}},{ '$push':{ "thread.$.replies": {'reply':new_post_count }}})

        # image files that have been attached
        if input_file: 
            content = cloudinary.uploader.upload(input_file)
            pic = cloudinary.CloudinaryImage(content["public_id"])
            media = pic.url
            if int(content["height"]) >= int(content["width"]):
                pic.url_options.update({"height":200})
                media_thumb = pic.url
            else:
                pic.url_options.update({"width":200})
                media_thumb = pic.url
        else:
           media = ""
           media_thumb = ""


        # the post and all its corresponding information is posted to the thread
        thread_update = { '$push':
                            { 'thread':
                                { 'message':message, 
                                'media':media,
                                'mediaThumb':media_thumb,
                                'posted':datetime.now(),
                                'formattedPosted':datetime.now().strftime("%b. %d, %Y %I:%M%p"),  
                                'postNum':new_post_count, 
                                'user':userid, 
                                'idColor':color,
                                'userIP':ip_address, 
                                'replies':[] 
                                }
                            }, 
                            '$set':
                                { 'formattedLastUpdated':datetime.now().strftime("%b. %d, %Y %I:%M%p"), 
                                'lastUpdated':datetime.now(), 
                                'posts':new_post_count
                                }
                            }
        mongo.db.threads.update_one({"_id":ObjectId(id)},thread_update)
        
        # the thread is then refreshed
        try:
            return redirect('/t/' + str(thread['_id']))
        except:
            return 'thread does not exist'
    else:
        thread = mongo.db.threads.find_one_or_404({'_id':ObjectId(id)})
        return render_template('thread.html', thread = thread, link = post_link, keyword = keyword)



if __name__ == "__main__":
    app.run(debug=True)
