USERNAME= "admin"
PASSWORD= "admim123"
MAX_ATTEMPTS = 3

for attempt in range(Max_ATTEMPTS):
    username = input("Enter your username: ")
    password = input("Enter your password: ")

    if username == USERNAME and password == PASSWORD:
        print("Login successful!")
        break
    else:
        print("Invalid username or password")


    