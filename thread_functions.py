import re

# first check is if there is nothing in the post.  Can't post an empty post
    # "error: post actual text and numbers and stuff, bruh..."
def no_message(msg, pattern, file):
    content = []
    for x in msg.split():
        if pattern.match(x) is None:
            content.append(x)

    if len(content) == 0:
        if file:
            return False
        else:
            return True
    else:
        return False

#################################
#### not really used anymore ####
# if this is true, error message is needed
    # "error: post actual text and numbers and stuff, bruh... not just mentions..."
def mentions_only(msg, pattern):
    iterate = msg.split()
    mentions_only = True
    for x in iterate:
        if pattern.match(x) is None:
            mentions_only = False
    return mentions_only
#### not really used anymore ####
#################################

# checks to see if the same user is posting the same shit over and over
def message_spam(msg, ip_address, thread):
    user_post_count = 0
    all_post_count = 0

    for post in thread['thread']:
        if ip_address == post['userIP']:
            if msg == post['message']:
                user_post_count += 1
                all_post_count += 1
        elif msg == post['message']:
            all_post_count += 1

    if user_post_count >= 3 or all_post_count >= 6:
        return True
    else:
        return False
