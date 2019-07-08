import os
import string
import random

if __name__ == "__main__":
    os.environ["SECRET"] = "".join(random.choices([char for char in string.printable if char not in string.whitespace], k=15))
    os.system("pip install -r \"requirements.txt\" --user")
    import app
    app.run()
