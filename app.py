from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import nltk
import pickle
from nltk.corpus import stopwords
import re
from nltk.stem.porter import PorterStemmer
from inspect import getmembers
from pprint import pprint

app = Flask(__name__)
ps = PorterStemmer()

app.secret_key = "your secret key"

# database
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "app_hoax"

mysql = MySQL(app)

# Load model and vectorizer
model = pickle.load(open("model2.pkl", "rb"))
tfidfvect = pickle.load(open("tfidfvect2.pkl", "rb"))
# Build functionalities


# crud admin
@app.route("/pengguna/", methods=["GET"])  # memanggil semua data
def pengguna():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT * FROM login""")
    rv = cur.fetchall()
    return render_template("pengguna.html", value=rv)


@app.route(
    "/pengguna/tambah_admin", methods=["GET", "POST"]
)  # menambahkan data pengguna
def tambah_admin():
    username = request.form["username"]
    password = request.form["password"]
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(
        "INSERT INTO login(username, password)VALUES(%s, %s)",
        (username, password),
    )
    mysql.connection.commit()
    return redirect(url_for("pengguna"))


@app.route("/pengguna/update_admin", methods=["POST"])  # mengedit data pengguna
def update_admin():
    id = request.form["id"]
    username = request.form["username"]
    password = request.form["password"]
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE login SET username=%s, password=%s WHERE id=%s",
        (
            username,
            password,
            id,
        ),
    )
    mysql.connection.commit()
    return redirect(url_for("pengguna"))


@app.route("/pengguna/hapus/<string:id>", methods=["GET"])  # hapus data pengguna
def delete_admin(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM login WHERE id=%s", (id,))
    mysql.connection.commit()
    return redirect(url_for("pengguna"))


# Route


@app.route("/login/tentang", methods=["GET"])
def tentang():
    return render_template("about.html")


@app.route("/login/", methods=["GET", "POST"])
def login():
    # Output message if something goes wrong...
    msg = ""
    if (
        request.method == "POST"
        and "username" in request.form
        and "password" in request.form
    ):
        # Create variables for easy access
        username = request.form["username"]
        password = request.form["password"]
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            "SELECT * FROM login WHERE username = %s AND password = %s",
            (
                username,
                password,
            ),
        )
        # Fetch one record and return result
        account = cursor.fetchone()
        # If account exists in accounts table in out database
        if account:
            # Create session data, we can access this data in other routes
            session["loggedin"] = True
            session["id"] = account["id"]
            session["username"] = account["username"]
            # Redirect to home page
            return redirect(url_for("dashboard"))
        else:
            # Account doesnt exist or username/password incorrect
            msg = "Incorrect username/password!"
    return render_template("login.html", msg=msg)


@app.route("/login/logout")
def logout():
    # Remove session data, this will log the user out
    session.pop("loggedin", None)
    session.pop("id", None)
    session.pop("username", None)
    # Redirect to login page
    return redirect(url_for("index"))


@app.route("/login/dashboard")
def dashboard():
    # Check if user is loggedin
    if "loggedin" in session:
        totalFakta = total_fakta()
        totalHoax = total_hoax()
        totalData = total_semua_data()
        totalPengguna = total_pengguna()
        # User is loggedin show them the home page
        return render_template(
            "dashboard.html",
            username=session["username"],
            totalFakta=totalFakta,
            totalHoax=totalHoax,
            totalData=totalData,
            totalPengguna=totalPengguna,
        )
    # User is not loggedin redirect to login page
    return redirect(url_for("login"))


# count total data
def total_fakta():
    cur = mysql.connection.cursor()
    cur.execute('SELECT count(hasil) from hasil_prediksi WHERE hasil="fakta" ')
    totalFakta = cur.fetchone()
    return totalFakta[0]


def total_hoax():
    cur = mysql.connection.cursor()
    cur.execute('SELECT count(hasil) from hasil_prediksi WHERE hasil="hoax" ')
    totalHoax = cur.fetchone()
    return totalHoax[0]


def total_semua_data():
    cur = mysql.connection.cursor()
    cur.execute("SELECT count(hasil) from hasil_prediksi ")
    totalData = cur.fetchone()
    return totalData[0]


def total_pengguna():
    cur = mysql.connection.cursor()
    cur.execute("SELECT count(id) from login ")
    totalPengguna = cur.fetchone()
    return totalPengguna[0]


@app.route("/login/hasil_prediksi")
def hasilprediksi():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT * FROM hasil_prediksi""")
    rv = cur.fetchall()
    return render_template("hasil_prediksi.html", value=rv)


@app.route("/login/hasil_prediksi/hapus/<string:id>")
def delete_prediksi(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM hasil_prediksi WHERE id=%s", (id,))
    # pprint(id)
    mysql.connection.commit()
    return redirect(url_for("hasilprediksi"))


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# menampilkan hasil


def predict(text):
    review = re.sub("[^a-zA-Z]", " ", text)
    review = review.lower()
    review = review.split()
    review = [
        ps.stem(word) for word in review if not word in stopwords.words("indonesian")
    ]
    review = " ".join(review)
    review_vect = tfidfvect.transform([review]).toarray()
    prediction = "HOAX" if model.predict(review_vect) == "HOAX" else "FAKTA"
    return prediction


@app.route("/", methods=["POST"])  # simpan data prediksi
def webapp():
    if request.method == "POST":
        text = request.form["text"]
        prediction = predict(text)
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO hasil_prediksi(text, hasil) VALUES (%s, %s)",
            (text, prediction),
        )
        mysql.connection.commit()
        return render_template("index.html", text=text, result=prediction)


@app.route("/predict/", methods=["GET", "POST"])
def api():
    text = request.args.get("text")
    prediction = predict(text)
    return jsonify(prediction=prediction)


if __name__ == "__main__":
    app.run()
