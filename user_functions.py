# function checking if the username already exists
    # might expand on this one as well
def username_error(uname):
    if len(uname) >= 3:
        if uname.isalnum() == True:
            return False
        else:
            return "Username must consist of letters and numbers only."
    else:
        return "Username needs to be 3 or more characters."


# function checking if the password is valid and in compliance
    # might expand on this in the future
def password_error(pass1, pass2):
    if pass1 == pass2:
        if len(pass1) >= 10:
            return False
        else:
            return "The password must be at least 10 characters long."
    else:
        return "The passwords do not match."
