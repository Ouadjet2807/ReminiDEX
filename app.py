import sqlite3
import datetime
import json
from flask import g, Flask, render_template, flash, redirect, request, session, jsonify
from flask_session import Session
from helpers import login_required
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

DATABASE = "flashcards.db"

def get_db():
    """Connexion to the SQLite database"""

    db = sqlite3.connect(DATABASE, timeout=30, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    """Create tables if they don't exist"""


    # Database tables:
    # users(id, username, hash)
    # lists(id, title, description, cards, folders, keywords, path, user_id, creation_date)
    # folders(id, name, path, keywords, user_id, creation_date)
    # lessons(id, cards, list_id, user_id, lesson_date)

    with get_db() as db:

        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            username TEXT NOT NULL,
            hash TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            cards TEXT,
            folders TEXT,
            keywords TEXT,
            path TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            creation_date DATE NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            keywords TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            creation_date DATE NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            cards TEXT NOT NULL,
            list_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            lesson_date DATE NOT NULL
        )""")


@app.context_processor
def inject_user():
    """Get username if logged in"""

    if "user_id" in session:
        user = {}
        with get_db() as db:
            user = db.execute("SELECT username FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        return dict(username=user["username"])
    return dict(username=None)

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.before_request
def before_request():
    init_db()

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET"])
@login_required
def index():
    """Get Home page and displays lists and folders"""

    user_id = session["user_id"]

    folders = []
    lists = []

    with get_db() as db:
        folders = db.execute("SELECT * FROM folders WHERE user_id = (?)", (user_id,)).fetchall()
        lists = db.execute("SELECT * FROM lists WHERE user_id = (?)", (user_id,)).fetchall()


    formatted_lists = []

    for list in lists:

        # Parse cards from JSON
        cards = json.loads(list["cards"])

        list_folders = []

        keywords = []

        # If folders exist parse, them from JSON
        if list["folders"]:
            list_folders = [str(f) for f in json.loads(list["folders"])]
        else:
            list_folders = []

        # If keywords exist parse, them from JSON
        if list["keywords"]:
            keywords = json.loads(list["keywords"])

        # Clean list object for better rendering
        formatted_lists.append({
            "id": list["id"],
            "title": list["title"],
            "description": list["description"],
            "cards": cards,
            "folders": list_folders,
            "keywords": keywords,
            "path": list["path"],
            "creation_date": list["creation_date"]
            }
            )

    return render_template("index.html", folders=folders, lists=formatted_lists)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure user has entered a username
        if not username:
            flash("You must enter your username", "danger")
            return redirect("/login")

        # Ensure user has entered a password
        elif not password:
            flash("You must enter your password", "danger")
            return redirect("/login")

        with get_db() as db:
            rows = db.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchall()

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            flash("Invalid username and/or password", "danger")
            return redirect("/login")

        # Forget any user id
        session.clear()
        session["user_id"] = rows[0]["id"]

        flash("Hello " + username + " !", "primary")

        return redirect("/")

    return render_template("login.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    """Log user out"""

    session.clear()

    flash("Logged out !", "primary")

    return redirect("/login")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user"""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure all inputs are correct

        if not username:
            flash("You must provide a username", "danger")
            return redirect("/register")
        elif not password:
            flash("You must provide a password", "danger")
            return redirect("/register")
        elif not confirmation:
            flash("You must confirm password", "danger")
            return redirect("/register")
        elif password != confirmation:
            flash("Passwords don't match", "danger")
            return redirect("/register")

        hash_password = generate_password_hash(password, method="pbkdf2:sha256")

        with get_db() as db:
            try:
                db.execute(
                    "INSERT INTO users (username, hash) VALUES (?, ?)",
                    (username, hash_password),
                )
            except sqlite3.IntegrityError:
                flash("Username already exists", "danger")
                return redirect("/register")


            row = db.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()

            session["user_id"] = row["id"]
            flash("Registered successfully!", "success")

        return redirect("/")

    return render_template("register.html")

@app.route("/account", methods=["GET"])
@login_required
def account():
    """Get account page and display lists number"""

    user_id = session["user_id"]

    list_number = 0

    with get_db() as db:
        row = db.execute("SELECT COUNT(*) FROM lists WHERE user_id = (?)", (user_id,)).fetchone()

        list_number = row["COUNT(*)"]

    return render_template("account.html", list_number=list_number)

@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    """Allow user to change their password"""

    user_id = session["user_id"]

    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirmation = request.form.get("confirmation")

    if not current_password:
        flash("You must enter your current password", "danger")
        return redirect("/account")

    if not new_password:
        flash("You must enter a new password", "danger")
        return redirect("/account")


    if not confirmation:
        flash("You must confirm your new password", "danger")
        return redirect("/account")


    with get_db() as db:

        user = db.execute("SELECT * FROM users WHERE id = (?)", (user_id,)).fetchone()

        # Ensure user has entered the correct password
        if not check_password_hash(user["hash"], current_password):
            flash("Invalid current password","danger")
            return redirect("/account")

        # Ensure new passwords match
        if new_password != confirmation:
            flash("New passwords don't match", "danger")
            return redirect("/account")

        new_password_hash = generate_password_hash(new_password, method="pbkdf2:sha256")

        db.execute("UPDATE users SET hash = (?) WHERE id = (?)", (new_password_hash, user_id))
        flash("Your password has been changed successfully !", "success")
        return redirect("/account")

@app.route("/delete_account", methods=["GET"])
@login_required
def delete_account():
    """Allow user to delete their account"""

    user_id = session["user_id"]

    with get_db() as db:

        db.execute("DELETE FROM users WHERE id = (?)", (user_id,))

    session.clear()

    return redirect("/")


@app.route("/create_list", methods=["GET", "POST"])
@login_required
def create_list():
    """
    Create or edit a list of flashcards.

    - GET: Preloads existing list data if editing
    - POST: Validates inputs, ensures at least two cards,
      and inserts/updates the list in the database.
    """

    preloaded_list_id = request.args.get("list")
    user_id = session["user_id"]

    page_title = "Create a new list"

    button_text = "Create list"

    creation_date = datetime.datetime.now()

    if request.method == "POST":
        list_id = request.form.get("id")
        list_title = request.form.get("title")
        list_description = request.form.get("description")
        cards_number = request.form.get("cards-number")


        cards = []

        for i in range(int(cards_number)):
            index = i + 1
            card_term = request.form.get(f"term_card_{index}")
            card_definition = request.form.get(f"definition_card_{index}")

            cards.append({
                "id": index,
                "term": card_term,
                "definition": card_definition,
                "level": ""
            })

        # Prevent list creation if fewer than two (non-empty) cards
        if int(cards_number) <= 2 and (cards[0]["term"] == "" and cards[0]["definition"] == "") or (cards[1]["term"] == "" and cards[1]["definition"] == ""):
            flash("You need at least two cards to create a list", "danger")
            return redirect("/create_list")


        cards_json = json.dumps(cards)

        with get_db() as db:

            lists_number = db.execute("SELECT COUNT(*) FROM lists").fetchone()

            lists_last_id = int(lists_number["COUNT(*)"])

            path = str.lower(str(list_title)) + "_" + str(lists_last_id + 1)

            if list_id == "/":
                db.execute(
                    "INSERT INTO lists (title, description, cards, path, user_id, creation_date) VALUES (?, ?, ?, ?, ?, ?)",
                    (list_title, list_description, cards_json, path, user_id, creation_date)
                )
                flash("List created successfully!", "success")
            else:
                db.execute(
                    "UPDATE lists SET title = (?), description = (?), cards = (?) WHERE id = (?) AND user_id = (?)",
                    (list_title, list_description, cards_json, list_id, user_id)
                )
                flash("List edited successfully!", "success")

        return redirect("/")

    preloaded_list = {}

    if preloaded_list_id:


        with get_db() as db:
            row = db.execute("SELECT * FROM lists WHERE id = (?) AND user_id = (?)", (preloaded_list_id, user_id)).fetchone()

            preloaded_list_cards = json.loads(row["cards"])

            page_title = "Edit " + str(row["title"])
            button_text = "Finish"

            # Format and clean up list
            preloaded_list = {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "cards": preloaded_list_cards,
                "path": row["path"],
                "creation_date": row["creation_date"]
            }


    return render_template("create_list.html", page_title=page_title, button_text=button_text, preloaded_list=preloaded_list)


@app.route("/create_folder", methods=["POST"])
@login_required
def create_folder():
    """Allow user to create folders"""

    user_id = session["user_id"]

    creation_date = datetime.datetime.now()

    name = request.form.get("name")

    if not name:
        flash("You must choose a folder name", "danger")
        return redirect("/")


    with get_db() as db:
        folders = db.execute("SELECT COUNT(*) FROM folders WHERE user_id = (?)", (user_id,)).fetchone()

        folders_last_id = int(folders["COUNT(*)"])

        path = str(str.lower((name))).replace(" ", "_") + "_" + str(folders_last_id + 1)


        db.execute("INSERT INTO folders (name, path, keywords, user_id, creation_date) VALUES (?, ?, ?, ?, ?)", (name, path, "[]", user_id, creation_date))


    return redirect("/")



@app.route("/delete_list", methods=["GET"])
@login_required
def delete_list():
    """Allow user to delete a listt / card deck"""

    user_id = session["user_id"]
    listId = request.args.get("list")
    listPath = request.args.get("list_path")

    if not listId:
        return redirect('user/lists/' + listPath)
    else:
        with get_db() as db:
            db.execute("DELETE FROM lists WHERE id = (?) AND user_id = (?)", (listId, user_id,))
            flash("The list has been successfully delete", "success")

        return redirect("/")


@app.route("/edit_folder", methods=["POST"])
@login_required
def edit_folder():
    """Allow user to edit folders"""

    user_id = session["user_id"]
    folderId = request.form.get("folder_id")
    folderPath = request.form.get("folder_path")
    folderName = request.form.get("folder_name")

    newPath = str(folderName) + "_" + str(folderId)


    if not folderId:
        return redirect('user/folders/' + folderPath)
    else:
        with get_db() as db:
            db.execute("UPDATE folders SET name = (?), path = (?) WHERE id = (?) AND user_id = (?)", (folderName, newPath, folderId, user_id,))
            flash("The folder has been successfully edited", "success")

    return redirect('user/folders/' + newPath)


@app.route("/delete_folder", methods=["GET"])
@login_required
def delete_folder():
    """Allow user to delete folders"""

    user_id = session["user_id"]
    folderId = request.args.get("folder")
    folderPath = request.args.get("folder_path")


    if not folderId:
        return redirect('user/folders/' + folderPath)
    else:
        with get_db() as db:
            db.execute("DELETE FROM folders WHERE id = (?) AND user_id = (?)", (folderId, user_id,))
            flash("The folder has been successfully delete", "success")

        return redirect("/")


@app.route("/user/folders/<folder_path>")
@login_required
def show_folder(folder_path):
    """Get selected folder page"""

    user_id = session["user_id"]
    folder = []
    lists = []
    lists_in_folder = []
    folder_id = ""

    with get_db() as db:
        folder_data = db.execute("SELECT * FROM folders WHERE path = (?)", (folder_path,)).fetchone()

        lists_data = db.execute("SELECT * FROM lists WHERE user_id = (?)", (user_id,)).fetchall()

        lists = [dict(list) for list in lists_data]


        folder = dict(folder_data)

        if folder:
            folder_id = folder["id"]

        if folder["keywords"]:
            folder["keywords"] = json.loads(folder["keywords"])

    for list in lists:
        list["cards"] = json.loads(list["cards"])

        if list["folders"]:
            list["folders"] = [str(f) for f in json.loads(list["folders"])]

        if list["keywords"]:
            list["keywords"] = json.loads(list["keywords"])

    for list in lists:

        if list["folders"] and str(folder_id) in list["folders"] and not list in lists_in_folder:
            lists_in_folder.append(list)

    return render_template("folder.html", folder=folder, folder_lists=lists_in_folder, all_lists=lists)


@app.route("/user/lists/<list_path>")
@login_required
def show_list(list_path):
    """Get selected list / card deck page"""

    user_id = session["user_id"]

    with get_db() as db:

        folders_list = db.execute("SELECT * FROM folders").fetchall()
        list_data = db.execute("SELECT * FROM lists WHERE path = (?)", (list_path,)).fetchone()

        list = dict(list_data)

        lessons = db.execute("SELECT * FROM lessons WHERE list_id = (?) AND user_id = (?) ORDER BY lesson_date DESC", (list["id"], user_id,)).fetchall()

        previous_lessons = [dict(r) for r in lessons]

        for lesson in previous_lessons:
            lesson["cards"] = json.loads(lesson["cards"])

        if list and list["folders"]:
            list["folders"] = json.loads(list["folders"])

        if list and list["keywords"]:
             list["keywords"] = json.loads(list["keywords"])

        list["cards"] = json.loads(list["cards"])

        previous_lessons.reverse()

        return render_template("list.html", list=list, list_path=list_path, folders_list=folders_list, lessons=previous_lessons)



@app.route("/add_to_folder", methods=["POST"])
@login_required
def add_to_folder():
    """Allow user to add list to folders"""

    user_id = session["user_id"]

    folder_path = request.form.get("folder_path")

    folder_id = request.form.get("folder_id")

    list_id = request.form.get("list_id")

    path = "/user/folders/" + str(folder_path)

    row = []

    with get_db() as db:

        row = db.execute("SELECT folders FROM lists WHERE id = (?) AND user_id = (?)", (list_id, user_id,)).fetchone()


    folders = []
    if row and row["folders"]:
        folders = json.loads(row["folders"])

    if folder_id not in folders:
        folders.append(folder_id)

    folders_json = json.dumps(folders)

    with get_db() as db:
        db.execute("UPDATE lists SET folders = (?) WHERE id = (?) AND user_id = (?)", (folders_json, list_id, user_id))


    return redirect(path)


@app.route("/remove_from_folder", methods=["POST"])
@login_required
def remove_from_folder():
    """Allow user to remove a list from folder"""

    user_id = session["user_id"]

    folder_id = request.form.get("folder_id")

    list_id = request.form.get("list_id")

    folder_path = request.form.get("folder_path")

    row = []

    path = "/user/folders/" + str(folder_path)

    with get_db() as db:

        row = db.execute("SELECT folders FROM lists WHERE id = (?) AND user_id = (?)", (list_id, user_id,)).fetchone()


    folders = []
    if row and row["folders"]:
        folders = json.loads(row["folders"])

    if folder_id in folders:
        folders.remove(folder_id)

    folders_json = json.dumps(folders)

    with get_db() as db:
        db.execute("UPDATE lists SET folders = (?) WHERE id = (?) AND user_id = (?)", (folders_json, list_id, user_id))


    return redirect(path)


@app.route("/create_keyword", methods=["POST"])
@login_required
def create_keyword():
    """Allow user to create keyword"""

    user_id = session["user_id"]

    keywordName = request.form.get("keyword")

    folderId = int(request.form.get("folder_id"))
    folderPath = request.form.get("folder_path")
    listId = int(request.form.get("list_id"))

    path = "/user/folders/" + str(folderPath)

    if not keywordName:
        flash("You must enter a keyword", "danger")

    with get_db() as db:
        listRow = db.execute("SELECT keywords FROM lists WHERE id = (?) AND user_id = (?)", (listId, user_id,)).fetchone()
        folderRow = db.execute("SELECT keywords FROM folders WHERE id = (?) AND user_id = (?)", (folderId, user_id,)).fetchone()

        folder_keywords = []
        list_keywords = []


        if folderRow["keywords"]:
            folder_keywords = json.loads(folderRow["keywords"])
        if listRow["keywords"]:
            list_keywords = json.loads(listRow["keywords"])

        folderKeyword = {
            "id": (len(list_keywords) + 1),
            "keyword": keywordName,
        }

        listKeyword = {
            "id": (len(list_keywords) + 1),
            "keyword": keywordName,
            "active": True
        }

        folder_keywords.append(folderKeyword)
        list_keywords.append(listKeyword)

        json_folder_keywords = json.dumps(folder_keywords)
        json_list_keywords = json.dumps(list_keywords)

        db.execute("UPDATE folders SET keywords = (?) WHERE id = (?) AND user_id = (?)", (json_folder_keywords, folderId, user_id))
        db.execute("UPDATE lists SET keywords = (?) WHERE id = (?) AND user_id = (?)", (json_list_keywords, listId, user_id))


    return redirect(path)


@app.route("/update_keyword_status", methods=["POST"])
@login_required
def update_keyword_status():
    """Update keyword in the table on toggle"""

    user_id = session["user_id"]
    data = request.get_json()
    list_id = data.get("list_id")
    keyword_id = data.get("keyword_id")
    active = True if data.get("active") else False


    with get_db() as db:
        keywords = db.execute("SELECT keywords FROM lists WHERE id = (?) AND user_id = (?)", (list_id, user_id,)).fetchone()

        print(keywords["keywords"])
        keywords = json.loads(keywords["keywords"])

        for keyword in keywords:
            if int(keyword["id"]) == int(keyword_id):
                keyword["active"] = active

        jsonKeywords = json.dumps(keywords)

        db.execute("""
            UPDATE lists
            SET keywords = (?)
            WHERE id = (?) AND user_id = ?
        """, (jsonKeywords, list_id, user_id))

    return jsonify(success=True)


@app.route("/update_card", methods=["POST"])
@login_required
def update_card():
    """Allow user to edit cards content"""

    user_id = session["user_id"]

    list_path = request.form.get("list_path")

    list_id = request.form.get("list_id")
    card_id = request.form.get("card_id")

    card_term = request.form.get("new_term")
    card_definition = request.form.get("new_definition")

    path = "/user/lists/" + str(list_path)

    if card_term == "" and card_definition == "":
        return redirect(path)

    with get_db() as db:
        cards = db.execute("SELECT cards FROM lists WHERE id = (?) AND user_id = (?)", (list_id, user_id,)).fetchone()
        cards = json.loads(cards["cards"])

        for card in cards:
            if card["id"] == int(card_id):
                card["term"] = card_term
                card["definition"] = card_definition


        jsonCards = json.dumps(cards)

        db.execute("UPDATE lists SET cards = (?) WHERE id = (?) AND user_id = (?)", (jsonCards, list_id, user_id))

    return redirect(path)


@app.route("/update_level", methods=["POST"])
@login_required
def update_level():
    """Change the card status (mastered or still learning) in the database"""

    user_id = session["user_id"]
    data = request.get_json()
    list_id = data["list_id"]
    list_cards = data["list_cards"]

    list = []

    with get_db() as db:
        cards = db.execute("SELECT cards FROM lists WHERE id = (?) AND user_id = (?)", (list_id, user_id,)).fetchone()

        cards = json.loads(cards["cards"])

        for list_card in list_cards:
            for card in cards:
                if int(card["id"]) == int(list_card["id"]):
                    card["level"] = list_card["level"]


        jsonCards = json.dumps(cards)

        db.execute("""
            UPDATE lists
            SET cards = (?)
            WHERE id = (?) AND user_id = ?
        """, (jsonCards, list_id, user_id))

        db.execute("""INSERT INTO lessons (cards, user_id, list_id, lesson_date) VALUES (?, ?, ?, ?)""", (jsonCards, user_id, list_id, datetime.datetime.now()))

        list = db.execute("SELECT * FROM lists WHERE id = (?) AND user_id = (?)", (list_id, user_id,)).fetchone()

    # Format and clean up list
    json_list = json.dumps({
        "id": list["id"],
        "title": list["title"],
        "description": list["description"],
        "cards": list["cards"],
        "folders": list["folders"],
        "keywords": list["keywords"],
        "path": list["path"],
        "user_id": list["user_id"],
    })

    return {"list": json_list}


