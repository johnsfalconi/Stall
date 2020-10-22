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
import hashlib
import random
import os
from dotenv import load_dotenv

# load .env file
load_dotenv()

app = Flask(__name__, static_folder="./static/")
app.config['MONGO_DBNAME'] = os.environ.get("MONGO_DBNAME") or os.getenv("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI") or os.getenv("MONGO_URI")
mongo = PyMongo(app)

def __repr__(self):
    return '<Task %r' % self.id

# Thread creation and index page generation with the list of threads.
@app.route("/", methods = ['POST', 'GET'])
def index():

    if request.method == 'POST':
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

    if request.method == 'POST':
        # increment post count for the thread document
        new_post_count = thread['posts'] + 1

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

        # the post and all its corresponding information is posted to the thread
        thread_update = { '$push':
                            { 'thread':
                                { 'message':request.form['message'], 
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
        return render_template('thread.html', thread = thread)



@app.route("/<keyword>/", methods = ['POST', 'GET'])
def boardIndex(keyword):
    if request.method == 'POST':
        try:
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
                    'formattedPosted':datetime.now().strftime("%b. %d, %Y %I:%M%p"), 
                    'postNum':1, 
                    'user':'OP', 
                    'idColor':'#ffffff',
                    'userIP':request.remote_addr, 
                    'replies':[] 
                } ]
            }
            x = mongo.db.threads.insert_one(new_thread)
            
            return redirect('/' + keyword + '/t/' + str(x.inserted_id))
        except:
            return 'There was an issue adding'
    else:
        if keyword == 't':
            return 'Invalid board name'
        else:
            threads = list(mongo.db.threads.find({'board':keyword}))
            return render_template('board.html', threads = threads, keyword = keyword)


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

    if request.method == 'POST':
        # increment post count for the thread document
        new_post_count = thread['posts'] + 1

        # getting ip address from the post request
        ip_address = request.remote_addr
        
        # this checks to see if the ip address has posted previously.  If not, a new user ID will be generated and stored
        if mongo.db.threads.find({'_id':ObjectId(id), 'threadUsers.ip':ip_address}).count() == 0:
            color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
            m = hashlib.md5()
            m.update(str(str(thread['_id']) + ip_address).encode('utf-8'))
            userid = str(m.hexdigest())[0:10]
            mongo.db.threads.update_one({'_id':ObjectId(id)},{'$push':{'threadUsers':{'ip':ip_address, 'userID':userid}}})
        # if the ip address was used before, this next block finds the corresponding user ID so it can be attached to the post
        else:
            for user in thread['threadUsers']:
                if user['ip'] == ip_address:
                    userid = user['userID']
                    color = user['idColor']

        # the post and all its corresponding information is posted to the thread
        thread_update = { '$push':
                            { 'thread':
                                { 'message':request.form['message'], 
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
            return redirect(url)
        except:
            return 'thread does not exist'
    else:
        thread = mongo.db.threads.find_one_or_404({'_id':ObjectId(id)})
        return render_template('thread.html', thread = thread, keyword = keyword)



if __name__ == "__main__":
    app.run(debug=True)
