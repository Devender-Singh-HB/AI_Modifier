import random
import string

def random_password(pass_len=12):
    symbols = list("!#$%&@^~")
    random.shuffle(symbols)

    lowercase = list(string.ascii_lowercase)
    random.shuffle(lowercase)

    uppercase = list(string.ascii_uppercase)
    random.shuffle(uppercase)

    digits = list(string.digits)
    random.shuffle(digits)

    all_character = symbols + lowercase + uppercase + digits
    random.shuffle(all_character)

    new_pass = list(random.choice(symbols) 
                + random.choice(lowercase) 
                + random.choice(uppercase) 
                + random.choice(digits))

    for _ in range(pass_len-4):
        new_pass.append(random.choice(all_character))
        random.shuffle(new_pass)

    return "".join(new_pass)

    

class temp_password:

    def __init__(self, password=None) -> None:
        self.password = password
    
    def save_password(self, password):
        self.password = password

    @property
    def get_password(self):
        password = self.password
        self.password = None
        return password