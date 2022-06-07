import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    result = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    cash = result[0]["cash"]
    portfolio = db.execute("SELECT symbol, shares FROM allstocks WHERE userid = ?", session["user_id"])
    grand_total = cash
    for stock in portfolio:
        d = lookup(stock['symbol'])
        price = d['price']
        name = d['name']
        shares = stock['shares']
        symbol = stock['symbol']
        total = stock['shares'] * price
        stock.update({'price': price, 'name': name, 'total': total})
        grand_total = grand_total + total
    return render_template("index.html", stocks=portfolio, cash=cash, total=grand_total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":  # form
        # check if symbol exists
        if not request.form.get("symbol").upper():
            return apology("PLEASE INPUT COMPANY SYMBOL", 400)
        if not lookup(request.form.get("symbol").upper()):
            return apology("SYMBOL DOESN'T EXIST", 400)
        if request.form.get("shares").isalnum() == False:
            return apology("BRUH", 400)
        if request.form.get("shares").isalpha() == True:
            return apology("BRUH ALL LETTERS?", 400)
        for i in range(0, len(str(request.form.get("shares")))):
            if str(request.form.get("shares"))[i].isalpha() == True:
                return apology("BRUH ALL NUMBERS!", 400)
        # s = str(request.form.get("shares"))
        # if isinstance(s,int) <=0:
            # return apology("MUST BE POSITIVE",400)
        cashleft = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        # if cannot afford so many shares
        if not cashleft:
            return apology("SMTH's WRONG!!!", 403)
        x = int(request.form.get("shares"))*lookup(request.form.get("symbol").upper())["price"]
        if int(request.form.get("shares"))*lookup(request.form.get("symbol").upper())["price"] > float(cashleft[0]["cash"]):
            return apology("CAN'T AFFORD", 400)
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]-x
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])
        # update transactions database (transaction_id, user_id, type, symbol, amount, price, time)
        db.execute("INSERT INTO transactions (user_id, type, symbol, amount, price, time) VALUES(?,?,?,?,?,?)", session["user_id"], "BUY", request.form.get(
            "symbol").upper(), request.form.get("shares"), lookup(request.form.get("symbol").upper())["price"], datetime.now())
        x = db.execute("SELECT * FROM allstocks WHERE userid=? AND symbol=?",
                       session["user_id"], request.form.get("symbol").upper())

        if len(x) != 0:
            # already has stock, change stock
            db.execute("UPDATE allstocks SET shares=? WHERE userid=? AND symbol=? LIMIT 1",
                       x[0]["shares"]+int(request.form.get("shares")), session["user_id"], request.form.get("symbol").upper())
        else:
            db.execute("INSERT INTO allstocks (userid, symbol, shares, name) VALUES(?,?,?,?)", session["user_id"], request.form.get(
                "symbol").upper(), request.form.get("shares"), lookup(request.form.get("symbol").upper())["name"])
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    histories = db.execute("SELECT symbol,type,amount,price,time FROM transactions WHERE user_id=?", session["user_id"])
    for transcn in histories:
        symbol = transcn["symbol"]
        if type == "SELL":
            amount = (-1) * transcn["amount"]
        else:
            amount = transcn["amount"]
        time = transcn["time"]
        price = transcn["price"]

    return render_template("history.html", histories=histories)
# user id, username, timestamp, company_symbol, shares, bought price


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1:
            return apology("invalid username", 400)
        elif not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("wrong password", 400)
        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # check if stock exists, name is "symbol"
    if request.method == "POST":  # submitted form
        if not request.form.get("symbol"):
            return apology("PLEASE INPUT COMPANY SYMBOL", 400)
        x = lookup(request.form.get("symbol").upper())
        if not x:
            return apology("SYMBOL DOESN'T EXIST", 400)
        # x exists, return to quoted
        return render_template("quoted.html", company=x)
    else:  # just visiting
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # if password/username invalid or null etc
        x = db.execute("SELECT username FROM users WHERE username = ?", request.form.get("username"))
        if(len(x) != 0):
            return apology("username already exists", 400)
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("password and confirmation dont match", 400)
        # hash + insert??
        if not request.form.get("username") or not request.form.get("password"):
            return apology("invalid username and/or password", 400)
        db.execute("INSERT INTO users (username,hash) VALUES(?, ?)", request.form.get(
            "username"), generate_password_hash(request.form.get("password")))
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        session["user_id"] = rows[0]["id"]
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        origshares = db.execute("SELECT shares FROM allstocks WHERE userid=? AND symbol=?",
                                session["user_id"], request.form.get("symbol").upper())
        if not origshares:
            return apology("YOU DON'T OWN ANY SHARES", 400)
        if int(request.form.get("shares")) > int(origshares[0]["shares"]):
            return apology("YOU CANNOT SELL MORE THAN YOU OWN", 400)
        if int(request.form.get("shares")) <= 0:
            return apology("PLEASE INPUT POSITIVE AMOUNT TO SELL", 400)
        # update transactions, users cash, allstocks
        # users cash
        x = int(request.form.get("shares"))*lookup(request.form.get("symbol").upper())["price"]
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]+x
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])
        # transactions
        db.execute("INSERT INTO transactions (user_id, type, symbol, amount, price, time) VALUES(?,?,?,?,?,?)", session["user_id"], "SELL", request.form.get(
            "symbol").upper(), request.form.get("shares"), lookup(request.form.get("symbol").upper())["price"], datetime.now())
        # allstocks
        x = db.execute("SELECT * FROM allstocks WHERE userid=? AND symbol=?",
                       session["user_id"], request.form.get("symbol").upper())
        if int(x[0]["shares"]) == int(request.form.get("shares")):
            # sell all, delete column of allstocks
            db.execute("DELETE FROM allstocks WHERE userid=? AND symbol=?", session["user_id"], request.form.get("symbol").upper())
        else:
            # update
            db.execute("UPDATE allstocks SET shares=? WHERE userid=? AND symbol=? LIMIT 1",

                       x[0]["shares"]-int(request.form.get("shares")), session["user_id"], request.form.get("symbol").upper())
        return redirect("/")
    else:
        possiblestocks = db.execute("SELECT symbol FROM allstocks WHERE userid=?", session["user_id"])
        return render_template("sell.html", possiblestocks=possiblestocks)

