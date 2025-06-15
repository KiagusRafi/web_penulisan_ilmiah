from flask import Flask


app = Flask(__name__)

# ini namanya "decorator"
@app.route('/')
def main(): 
    #kolor babe
    print("kancud")


if __name__=="__main__":
    app.run()