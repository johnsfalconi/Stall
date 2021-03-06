from flask import Flask, render_template, url_for, request, redirect, session
from flask_pymongo import PyMongo
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from bson.objectid import ObjectId
from datetime import datetime
from dotenv import load_dotenv
from passlib.hash import sha256_crypt
from thread_functions import no_message, message_spam, user_spam, emoji_check, nested_return
from user_functions import username_error, password_error
import cloudinary
import cloudinary.uploader
import cloudinary.api
import functools
import hashlib
import random
import re
import os

# load .env file
load_dotenv()

app = Flask(__name__, static_folder="./static/")
app.config['MONGO_DBNAME'] = os.environ.get("MONGO_DBNAME") or os.getenv("MONGO_DBNAME")
app.config['MONGO_URI'] = os.environ.get("MONGO_URI") or os.getenv("MONGO_URI")
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY") or os.getenv("SECRET_KEY")
mongo = PyMongo(app)

login = LoginManager()
login.init_app(app)
login.login_view = 'login'

cloudinary.config(cloud_name = (os.environ.get("CLOUD_NAME") or os.getenv("CLOUD_NAME")), 
    api_key = (os.environ.get("API_KEY") or os.getenv("API_KEY")), 
    api_secret = (os.environ.get("API_SECRET") or os.getenv("API_SECRET")))


def __repr__(self):
    return '<Task %r' % self.id


# Thread creation and index page generation with the list of threads.
@app.route("/", methods = ['POST', 'GET'])
def index():

    threads = list(mongo.db.threads.find({'board':'Global', 'type':'General'}))
    stickies = list(mongo.db.threads.find({'board':'Global', 'type':'Sticky'}))
    dailies = list(mongo.db.threads.find({'board':'Global', 'type':'Daily'}))
    board = list(mongo.db.boards.find({'board':'Global'}))
    mods = board[0]['moderators']
    return render_template("index.html", threads = threads, stickies = stickies, dailies = dailies, keyword = 'Global', mods = mods)
    

@app.route("/sticky/<id>", methods = ['POST', 'GET'])
def sticky(id):
    try:
        mongo.db.threads.update_one({'_id':ObjectId(id)},{'$set':{'type':'Sticky'}})
        return redirect('/')
    except:
        return 'there was a problem stickying'

@app.route("/unsticky/<id>", methods = ['POST', 'GET'])
def unsticky(id):
    try:
        mongo.db.threads.update_one({'_id':ObjectId(id)},{'$set':{'type':'General'}})
        return redirect('/')
    except:
        return 'there was a problem un-stickying'

# new thread submission
@app.route("/new/", methods = ['POST', 'GET'])
def new_thread():

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

        message = emoji_check(request.form['post'])

        try:
            # this is all stored as a variable so it can be laid out for readability
            new_thread = {
                'title':str(request.form['title']), 
                'board':'Global',
                'type': 'General', 
                'formattedDate':str(datetime.now().strftime("%b. %d, %Y")), 
                'date':datetime.now(), 
                'preview':message, 
                'formattedLastUpdated':datetime.now().strftime("%b. %d, %Y %I:%M%p"), 
                'lastUpdated':datetime.now(), 'posts':1, 
                'threadUsers':[ { 'ip':request.remote_addr, 'userID':'OP', 'idColor':'#ffffff'  } ],
                'thread':[ { 
                    'message':message, 
                    'media':media,
                    'mediaThumb':media_thumb,
                    'formattedPosted':datetime.now().strftime("%b. %d, %Y %I:%M%p"),
                    'posted': datetime.now(),
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
        return render_template("new_thread.html", keyword = 'Global')


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
    cust_moji = re.compile(r'^\:[A-Za-z0-9_-]\:')

    if request.method == 'POST':
        # increment post count for the thread document
        new_post_count = thread['posts'] + 1
        message = emoji_check(request.form['message'])
        input_file = request.files["media"]

        # getting ip address from the post request
        ip_address = request.remote_addr

        # spam prevention
            #   no text or all spaces -> error: post actual text and numbers and stuff, bruh
            #   the only post are reply links -> error: post actual text and numbers and stuff, bruh... not just mentions...
            #   the same message from the same person over 3 times -> error: we get it... post something else.
            #   the same message 6 times in the thread by anyone -> error: we get it... post something else.
        time_diff = user_spam(ip_address, thread)

        if no_message(message, post_link, input_file) == True:
            return render_template('thread.html', thread = thread, link = post_link, error = "error: post actual text and numbers and stuff, bruh")
        elif message_spam(message, ip_address, thread) == True:
            return render_template('thread.html', thread = thread, link = post_link, error = "error: we get it... post something else.")
        elif time_diff <= 45:
            return render_template('thread.html', thread = thread, link = post_link, error = "error: slooowwwwww doooowwwwwnnnnn (wait like " + str(45 - time_diff) + " more seconds)")
        else:
            
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
                # should probably update this to a separate function
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
        board = list(mongo.db.boards.find({'board':'Global'}))
        mods = board[0]['moderators']
        thread = mongo.db.threads.find_one_or_404({'_id':ObjectId(id)})
        return render_template('thread.html', thread = thread, link = post_link, error = "none", mods = mods, nested_return = nested_return)



# @app.route("/<keyword>/", methods = ['POST', 'GET'])
# def boardIndex(keyword):
#     if request.method == 'POST':
#         input_file = request.files["media"]

#         if input_file: 
#             content = cloudinary.uploader.upload(input_file)
#             pic = cloudinary.CloudinaryImage(content["public_id"])
#             media = pic.url
#             if int(content["height"]) >= int(content["width"]):
#                 pic.url_options.update({"height":400})
#                 media_thumb = pic.url
#             else:
#                 pic.url_options.update({"width":400})
#                 media_thumb = pic.url
#         else:
#             media = ""
#             media_thumb = ""

#         try:
#             # this is all stored as a variable so it can be laid out for readability
#             new_thread = {
#                 'title':str(request.form['title']), 
#                 'board':keyword, 
#                 'formattedDate':str(datetime.now().strftime("%b. %d, %Y")), 
#                 'date':datetime.now(),  
#                 'formattedLastUpdated':datetime.now().strftime("%b. %d, %Y %I:%M%p"), 
#                 'lastUpdated':datetime.now(), 'posts':1, 
#                 'threadUsers':[ { 'ip':request.remote_addr, 'userID':'OP', 'idColor':'#ffffff'  } ],
#                 'thread':[ { 
#                     'message':request.form['post'], 
#                     'media':media,
#                     'mediaThumb':media_thumb,
#                     'formattedPosted':datetime.now().strftime("%b. %d, %Y %I:%M%p"), 
#                     'postNum':1, 
#                     'user':'OP', 
#                     'idColor':'#ffffff',
#                     'userIP':request.remote_addr, 
#                     'replies':[] 
#                 } ]
#             }
#             # the actual insert_one statement saved to a variable so the new document's _id can be referenced
#             x = mongo.db.threads.insert_one(new_thread)
            
#             #redirect using the thread app route to bring the user to the newly-inserted thread
#             return redirect('/' + keyword + '/t/' + str(x.inserted_id))

#         except:
#             return 'There was an issue adding'
#     else:
#         threads = list(mongo.db.threads.find({'board':keyword}))
#         return render_template("index.html", threads = threads, keyword = keyword)


# @app.route('/<keyword>/delete/<id>')
# def boardDelete(id, keyword):
#     try:
#         mongo.db.threads.delete_one({"_id":ObjectId(id)})
#         return redirect('/' + keyword + '/')
#     except:
#         return 'there was a problem deleting'



# @app.route('/<keyword>/t/<id>', methods = ['GET', 'POST'])
# def boardT(keyword, id):
#     thread = mongo.db.threads.find_one_or_404({'_id':ObjectId(id)})
#     url = request.url
#     post_link = re.compile(r'^\[[0-9]+\]')

#     if request.method == 'POST':
#         # increment post count for the thread document
#         new_post_count = thread['posts'] + 1
#         message = request.form['message']
#         input_file = request.files["media"]

#         # getting ip address from the post request
#         ip_address = request.remote_addr
        
#         # this checks to see if the ip address has posted previously.  If not, a new user ID will be generated and stored
#         if mongo.db.threads.find({'_id':ObjectId(id), 'threadUsers.ip':ip_address}).count() == 0:
#             color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
#             m = hashlib.md5()
#             m.update(str(str(thread['_id']) + ip_address).encode('utf-8'))
#             userid = str(m.hexdigest())[0:10]
#             mongo.db.threads.update_one({'_id':ObjectId(id)},{'$push':{'threadUsers':{'ip':ip_address, 'userID':userid, 'idColor':color}}})
#         # if the ip address was used before, this next block finds the corresponding user ID so it can be attached to the post
#         else:
#             for user in thread['threadUsers']:
#                 if user['ip'] == ip_address:
#                     userid = user['userID']
#                     color = user['idColor']

#         # the message is then parsed through to find all the post replies
#         replies = []

#         for line in message.split('\n'):
#             if len(line) > 0:
#                 if line[0] != '>':
#                     for word in line.split(' '):
#                         if post_link.match(word):
#                             if new_post_count != int(word.replace('[', '').replace(']','')):
#                                 for post in thread['thread']:
#                                     if post['postNum'] == int(word.replace('[', '').replace(']','')):
#                                         replies.append(post['postNum'])

#         for reply in list(set(replies)):
#             mongo.db.threads.update_one({"_id":ObjectId(id), "thread":{ "$elemMatch": {"postNum":reply}}},{ '$push':{ "thread.$.replies": {'reply':new_post_count }}})

#         # image files that have been attached
#         if input_file: 
#             content = cloudinary.uploader.upload(input_file)
#             pic = cloudinary.CloudinaryImage(content["public_id"])
#             media = pic.url
#             if int(content["height"]) >= int(content["width"]):
#                 pic.url_options.update({"height":200})
#                 media_thumb = pic.url
#             else:
#                 pic.url_options.update({"width":200})
#                 media_thumb = pic.url
#         else:
#            media = ""
#            media_thumb = ""


#         # the post and all its corresponding information is posted to the thread
#         thread_update = { '$push':
#                             { 'thread':
#                                 { 'message':message, 
#                                 'media':media,
#                                 'mediaThumb':media_thumb,
#                                 'posted':datetime.now(),
#                                 'formattedPosted':datetime.now().strftime("%b. %d, %Y %I:%M%p"),  
#                                 'postNum':new_post_count, 
#                                 'user':userid, 
#                                 'idColor':color,
#                                 'userIP':ip_address, 
#                                 'replies':[] 
#                                 }
#                             }, 
#                             '$set':
#                                 { 'formattedLastUpdated':datetime.now().strftime("%b. %d, %Y %I:%M%p"), 
#                                 'lastUpdated':datetime.now(), 
#                                 'posts':new_post_count
#                                 }
#                             }
#         mongo.db.threads.update_one({"_id":ObjectId(id)},thread_update)
        
#         # the thread is then refreshed
#         try:
#             return redirect('/t/' + str(thread['_id']))
#         except:
#             return 'thread does not exist'
#     else:
#         thread = mongo.db.threads.find_one_or_404({'_id':ObjectId(id)})
#         return render_template('thread.html', thread = thread, link = post_link, keyword = keyword, error = "none")


@app.route('/boards/', methods = ['GET', 'POST'])
def boards():
    return render_template('boards.html', keyword = "Global")


@app.route('/archives/', methods = ['GET', 'POST'])
def archives():
    return render_template('archives.html', keyword = "Global")


class User:
    def __init__(self, username, ty):
        self.username = username
        self.type = ty

    @staticmethod
    def is_authenticated():
        return True

    @staticmethod
    def is_active():
        return True

    @staticmethod
    def is_anonymous():
        return False

    def get_id(self):
        return self.username

    @staticmethod
    def check_password(password_hash, password):
        return check_password_hash(password_hash, password)


    @login.user_loader
    def load_user(username):
        u = mongo.db.users.find_one({"username": username})
        if not u:
            return None
        return User(username=u['username'], ty = u['type'])

    @app.route('/login/', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            user = mongo.db.users.find_one({"username": request.form['username']})
            if user and sha256_crypt.verify(request.form['password'], user['password']):
                user_obj = User(username=user['username'], ty=user['type'])
                login_user(user_obj)
                return redirect('/')
            else:
                return render_template('login.html', keyword = "Global")
        return render_template('login.html', keyword = "Global")

    @app.route('/logout/')
    def logout():
        logout_user()
        return redirect('/')


@app.route('/register/', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password1 = request.form['password']
        password2 = request.form['password2']

        u_error = username_error(username)
        p_error = password_error(password1, password2)

        user_list = list(mongo.db.users.find({'username':username}))
        if len(user_list) > 0:
            u_error2 = 'Username already exists.'
        else:
            u_error2 = False

        if u_error != False:
            return render_template('register.html', error = u_error, keyword = "Global")
        if u_error2 != False:
            return render_template('register.html', error = u_error2, keyword = "Global")
        elif p_error != False:
            return render_template('register.html', error = p_error, keyword = "Global")
        else:
            pass_hash = sha256_crypt.encrypt(password1)
            new_user = {
                'username':username, 
                'password':pass_hash,
                'formattedDate':str(datetime.now().strftime("%b. %d, %Y")), 
                'date':datetime.now(),
                'type':'User'
            }
            mongo.db.users.insert_one(new_user)
            user_obj = User(username=username, ty = 'User')
            login_user(user_obj)
            return redirect('/')

    else:
        return render_template('register.html', error = 'none', keyword = "Global")

@app.route('/users/<username>', methods = ['GET', 'POST'])
def profile(username):
    return render_template('profile.html', username = username)

@app.route('/users/', methods = ['GET', 'POST'])
def users():
    return render_template('users.html')

if __name__ == "__main__":
    app.run(debug=True)

