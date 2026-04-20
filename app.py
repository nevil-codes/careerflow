from flask import Flask, render_template

app = Flask(__name__)

jobs = []


@app.route("/")
def dashboard():
    return render_template("index.html", jobs=jobs)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
