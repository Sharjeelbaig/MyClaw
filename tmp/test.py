import os
if os.uname().sysname == "Darwin":
    print("mac")
elif os.uname().sysname == "Linux":
    print("linux")
    