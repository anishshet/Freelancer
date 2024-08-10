import sqlite3
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    flash,
    session,
)
from datetime import datetime
from celery import Celery
from flask_cors import CORS
from collections import defaultdict
from datetime import datetime
import sys
import sqlite3
import os
import redis
from flask_session import Session
app = Flask(__name__)
CORS(app, origins=["http://localhost:8080"])
app.secret_key = "__privatekey__"
app.static_folder = "static"

app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REDIS'] = redis.from_url('redis://127.0.0.1:6379')

simple_app = Celery('simple_worker', broker='redis://127.0.0.1:6379/0', backend='redis://127.0.0.1:6379/0')

conn = sqlite3.connect("user_data.db", check_same_thread=False)
cursor = conn.cursor()

app.config["UPLOAD_FOLDER"] = "uploads"

session = {}
# simple_app.conf.update(app.config)
redis_client = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
song_data = []
@simple_app.task
def fetch_recent_songs(uploadsong_id):
    try:
        conn = sqlite3.connect("user_data.db", check_same_thread=False)
        cursor = conn.cursor()
        
        print(f"uploadsong_id: {uploadsong_id}")
        
          # Initialize an empty list to store songs
        cursor.execute(f"SELECT title, genre, artist, duration, date FROM uploadsong WHERE uploadsong_id = {uploadsong_id};")
        song_data.extend(cursor.fetchall())

        cursor.execute("SELECT Click_Date_Time FROM Recent_songs WHERE uploadsong_id = ?", (uploadsong_id,))
        conn.commit()
        existing_record = cursor.fetchone()
        print(f"existing_record : {existing_record}")
        if existing_record:
            conn = sqlite3.connect("user_data.db", check_same_thread=False)
            cursor = conn.cursor()

            current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("UPDATE Recent_songs SET Click_Date_Time = ? WHERE uploadsong_id = ?", (current_datetime, uploadsong_id))
        else:
            conn = sqlite3.connect("user_data.db", check_same_thread=False)
            cursor = conn.cursor()

            current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("INSERT INTO Recent_songs (uploadsong_id, Click_Date_Time) VALUES (?, ?)", (uploadsong_id, current_datetime))
        
        conn.commit()
        data = {"song": song_data}
        return data
    
    except sqlite3.Error as sqlite_error:
        return {"error": f"SQLite error: {str(sqlite_error)}"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}
    finally:
        conn.close()

@app.route("/", methods=['GET', 'POST'])
def fetchedsongdata():
    try:
        if request.method=='GET':

            if "username" not in session:
                return jsonify({"error":"Kindly login"}), 401
            conn = sqlite3.connect("user_data.db")
            cursor = conn.cursor()

            cursor.execute(
                "SELECT uploadsong_id, AVG(rating) FROM Likes GROUP BY uploadsong_id ORDER BY AVG(rating) DESC"
            )
            uploadsong_ids = cursor.fetchall()
            uploadsong_ids = [uploadsong_id[0] for uploadsong_id in uploadsong_ids]

            songs = []
            
            for uploadsong_id in uploadsong_ids:
                conn = sqlite3.connect("user_data.db", check_same_thread=False)
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM uploadsong WHERE uploadsong_id = ?", (uploadsong_id,)
                )
                song = cursor.fetchone()
                cursor.execute(
                    "SELECT AVG(rating) FROM Likes WHERE uploadsong_id = ?",
                    (uploadsong_id,),
                )
                avg_rating = cursor.fetchone()
                avg_rating = avg_rating[0] if avg_rating is not None else 0

                if song is not None:
                    song = list(song)
                    song.append(avg_rating)
                    song = tuple(song)
                    songs.append(song)
            cursor.execute(
                "SELECT * FROM uploadsong WHERE uploadsong_id NOT IN (SELECT uploadsong_id FROM Likes)"
            )
            unrated_songs = cursor.fetchall()
            songs.extend(unrated_songs)

            cursor.execute("SELECT * FROM Albums")
            albums_data = cursor.fetchall()

            cursor.execute("SELECT DISTINCT genre FROM uploadsong")
            genre_data = cursor.fetchall()

            cursor.execute("SELECT DISTINCT artist FROM uploadsong")
            artist_date_data = cursor.fetchall()

            username = session["username"]
            cursor.execute(
                "SELECT Playlist_ID, name FROM Playlists WHERE username = ?", (username,)
            )
            playlists = cursor.fetchall()
            data = {
                "songs": songs,
                "albums_data": albums_data,
                "genre_data": genre_data,
                "artist_date_data": artist_date_data,
                "playlists": playlists,
                }

            return jsonify(data)
        
        elif request.method=='POST':
            try:
                data = request.json
                uploadsong_id = data.get("uploadsong_id")
                
                recent_songs_result = fetch_recent_songs(uploadsong_id)
                print(recent_songs_result)
                data = {
                "recent_songs": recent_songs_result
                }
                return jsonify(data)
            except sqlite3.Error as sqlite_error:
                return jsonify({"error": f"SQLite error: {str(sqlite_error)}"})

            except Exception as e:
                return jsonify({"error": f"Error: {str(e)}"})
        
    except KeyError as key_error:
        return jsonify({"error": f"KeyError: {str(key_error)}: 'username' key not found in session"})
    
    except sqlite3.Error as sqlite_error:
        return jsonify({"error": f"SQLite error: {str(sqlite_error)}"})

    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"})

@app.route("/loginuser", methods=["POST"])
def login_user():   
    if request.method == "POST":
        data = request.json
        username = data.get("username")
        password = data.get("password")
    
        # Check credentials against database (use parameterized queries to prevent SQL injection)
        query = f"SELECT username, password FROM user WHERE username = '{username}' AND password = '{password}'"
        conn = sqlite3.connect("user_data.db")
        cursor = conn.cursor()
        cursor.execute(query)

        results = cursor.fetchall()
        conn.close()

        if len(results) == 0:
            return jsonify({"error": "Wrong credentials provided"}), 401
        else:
            # Store username in session
            session["username"] = username

            # Retrieve email and store in session if not already present
            if "email" not in session:
                conn = sqlite3.connect('user_data.db')
                cursor = conn.cursor()
                cursor.execute(f"SELECT email FROM user WHERE username = '{username}'")
                email = cursor.fetchone()
                conn.close()

                if email is not None:
                    email = email[0]
                    session["email"] = email
            print(session)
            return jsonify({"message": "Login successful", "session": dict(session)}), 200

    return jsonify({"error": "Method not allowed"}), 405

@app.route("/registeruser", methods=["POST"])
def register_user():
    if request.method == "POST":
        data = request.json
        name = data.get("name")
        email = data.get("email")
        username = data.get("username")
        password = data.get("password")
        print(name)
        # Connect to the database
        conn = sqlite3.connect('user_data.db')
        cursor = conn.cursor()

        # Check if username already exists
        cursor.execute(f"SELECT * FROM user WHERE username = '{username}'")
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return jsonify({"error": "Username already exists, login instead"}), 400
        else:
            # Insert new user into the database
            cursor.execute(f"INSERT INTO user (name, username, email, password, isAdmin) VALUES ('{name}', '{username}', '{email}', '{password}', '{0}')")
            conn.commit()
            session["username"] = username
            session["email"] = email
            conn.close()
            return jsonify({"message": "Registration successful, please login"}), 200

    return jsonify({"error": "Method not allowed"}), 405

@app.route("/logout", methods=["POST"])
def logout_user():
    print(session)
    # redis_client.flushall()

    session.clear()
    return jsonify({"message": "Logout successful"}), 200

@app.route("/loginadmin", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        data = request.json
        username = data.get("username")
        password = data.get("password")
        conn = sqlite3.connect('user_data.db')
        cursor = conn.cursor()

        query = f"SELECT username, password from admin WHERE username = '{username}' AND password = '{password}'"
        cursor.execute(query)

        results = cursor.fetchall()
        print(results)
        if len(results) == 0:
            return jsonify({"error": "Wrong credentials"}), 400
        else:
            cursor.execute(f"SELECT isAdmin FROM admin WHERE username='{username}'")
            is_admin = cursor.fetchone()

            session["isAdmin"] = is_admin[0] if is_admin else 0
            session["username"] = username
            return jsonify({"message":"Login Admin Succesfull"}), 200
    return jsonify({"error": "Method not allowed"}), 405

@app.route("/logoutadmin", methods=["GET", "POST"])
def logout_admin():
    # redis_client.flushall()

    session.clear()
    return jsonify({"message": "Logout successful"}), 200

@app.route("/creator", methods=["GET", "POST"])
def creator():
    if request.method == "GET":
        print(session)
        if "email" in session:
            email = session["email"]
            conn = sqlite3.connect("user_data.db")
            cursor = conn.cursor()
            cursor.execute(f"SELECT creator_id FROM creator WHERE email = '{email}'")
            artist_id = cursor.fetchone()
            if artist_id is not None:
                artist_id = artist_id[0]
                session["artist_id"] = artist_id
                return jsonify({"message": "Success", "artist_id": artist_id})
            else:
                return jsonify({"error": "Please select a genre"}), 400
        else:
            return jsonify({"error": "Please login first"}), 401
    else:
        data = request.json
        genre = data.get("genre")
        conn = sqlite3.connect("user_data.db")
        cursor = conn.cursor()
            
        print(session)
        # if email not in session:
        #     return jsonify({"message":"Login please"})
        email = session["email"]
        artist = data.get("artist")
        if artist == "":
            return jsonify({"error": "Please enter artist name"}), 400
        if genre == "":
            return jsonify({"error": "Please select a genre"}), 400
        cursor.execute(
            "INSERT INTO creator (artist, email, genre) VALUES (?, ?, ?)",
            (artist, email, genre),
        )
        conn.commit()
        cursor.execute("SELECT creator_id FROM creator WHERE email = ?", (email,))
        artist_id = cursor.fetchone()
        if artist_id is not None:
            artist_id = artist_id[0]
            session["artist_id"] = artist_id
            return jsonify({"message": "Success", "artist_id": artist_id}), 200
        else:
            return jsonify({"error": "Error in selecting genre"}), 500

@app.route("/userfetchesalbum/<id>", methods=["GET"])
def fetch_album(id):
    # select all songs from uploadsong table where album_id = id, and prepare list in manner we have prepared in home route
    cursor.execute("SELECT * FROM uploadsong WHERE album_id = ?", (id,))
    songs = cursor.fetchall()
    songs = [song for song in songs]
    cursor.execute("SELECT Album_name FROM Albums WHERE Album_ID = ?", (id,))
    album_name = cursor.fetchone()[0]
    
    return render_template("userfetchesalbum.html", songs=songs, album_name=album_name)

@app.route("/createplaylist", methods=["GET", "POST"])
def create_playlist():
    if request.method == "GET":
        if "username" in session:
            # Fetch all songs from uploadsong table only their id and title
            cursor.execute("SELECT uploadsong_id, title FROM uploadsong")
            songs = cursor.fetchall()
            songs = [song for song in songs]
            return render_template("playlistcreate.html", songs=songs)
        else:
            return render_template("loginuser.html", message="Please login first")

    if request.method == "POST":
        if "username" not in session:
            return render_template("loginuser.html", message="Please login first")

        username = session.get("username")  # Use .get() to avoid KeyError
        if username is None:
            return render_template(
                "loginuser.html", message="Username not found in session"
            )

        playlist_name = request.form["playlist_name"]
        songs = request.form.getlist("songs")

        if not playlist_name:
            return render_template("error.html", message="Playlist name is required")

        if not songs:
            return render_template(
                "error.html", message="Select at least one song for the playlist"
            )

        print("Username:", username)
        print("Playlist Name:", playlist_name)
        print("Selected Songs:", songs)

        try:
            # Insert into Playlists table
            cursor.execute(
                "INSERT INTO Playlists (Name, username) VALUES (?,?)",
                (
                    playlist_name,
                    username,
                ),
            )
            conn.commit()
            # Get the Playlist_ID for the newly inserted playlist
            cursor.execute(
                "SELECT Playlist_ID FROM Playlists WHERE Name = ? AND username = ?",
                (
                    playlist_name,
                    username,
                ),
            )

            playlist_id = cursor.fetchone()[0]

            # Insert into Playlist_Tracks table
            for song in songs:
                cursor.execute(
                    "INSERT INTO Playlist_Tracks (Playlist_ID, uploadsong_id) VALUES (?,?)",
                    (
                        playlist_id,
                        song,
                    ),
                )
                conn.commit()

            # Commit changes to the database

            return render_template(
                "playlistcreate.html", message="Playlist created successfully"
            )

        except Exception as e:
            print("Error:", str(e))
            # Rollback changes in case of an error
            conn.rollback()

    return render_template("playlistcreate.html")

@app.route("/uploadsong", methods=["POST"])
def upload():
    if request.method == "POST":

        title = request.form["title"]
        artist = request.form["artist"]
        genre = request.form["genre"]
        duration = request.form["duration"]
        Album_name = request.form["Album_name"]
        date = request.form["date"]
        if "uploaded_file" not in request.files:
            return jsonify({"error": "No file part"}), 400
        uploaded_file = request.files["uploaded_file"]
        filename = uploaded_file.filename
        lyrics = request.form["lyrics"]
        cursor.execute("SELECT creator_id FROM creator WHERE artist = ?", (artist,))
        creator_id = cursor.fetchone()

        if creator_id is not None:
            creator_id = creator_id[0]
        else:
            return jsonify({"error": "Please register as a creator first"})

        cursor.execute(
            "SELECT Album_ID FROM Albums WHERE Album_name = ? AND Artist_ID = ? ",
            (
                Album_name,
                creator_id,
            ),
        )
        album_id = cursor.fetchone()
        if album_id is not None:
            album_id = album_id[0]
        else:
            # creating new album if album not found, giving attributes Artist_ID, Album_name and Release_Date ( same as songs date)
            cursor.execute(
                "INSERT INTO Albums (Artist_ID, Album_name, Release_Date) VALUES (?, ?, ?)",
                (
                    creator_id,
                    Album_name,
                    date,
                ),
            )
            return jsonify({
            "message": "Album not found, created one new by the name '" + Album_name + "' for you, now upload song with this album name if you want to add more songs to this album"
        })

        filename = datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + filename
        print(filename)
        uploaded_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        cursor.execute(
            "INSERT INTO uploadsong (title, artist, genre, duration, date, filename, lyrics, isFlagged, creator_id, album_id) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (
                title,
                artist,
                genre,
                duration,
                date,
                filename,
                lyrics,
                creator_id,
                album_id,
            ),
        )
        conn.commit()
        # conn.close()
        return jsonify({"message": "Song uploaded successfully"})

@app.route("/genre/<id>", methods=["GET"])
def genre(id):
    # user explores genre with name = id, in this route user will be shown all songs in that genre
    cursor.execute("SELECT * FROM uploadsong WHERE genre = ?", (id,))
    songs = cursor.fetchall()
    songs = [song for song in songs]
    return render_template("usergenre.html", songs=songs,GenreName=id)

@app.route("/playlist/<id>", methods=["GET"])
def playlist(id):
    if request.method == "GET":
        if "username" in session:
            # Fetch all songs from uploadsong table only their id and title
            cursor.execute(
                "SELECT uploadsong_id, title FROM uploadsong WHERE uploadsong_id IN (SELECT uploadsong_id FROM Playlist_Tracks WHERE Playlist_ID = ?)",
                (id,),
            )
            songs = cursor.fetchall()
            songs = [{"uploadsong_id": song[0], "title": song[1]} for song in songs]
            
            cursor.execute(
                "SELECT name FROM Playlists WHERE Playlist_ID = ?", (id,)
            )
            playlist_name = cursor.fetchone()[0]
            
            return jsonify({"songs": songs, "PlaylistName": playlist_name})
        else:
            return jsonify({"message": "Please login first"}), 401
        
@app.route("/creatorsdash", methods=["GET"])
def creatorsdash():
    if "email" not in session:
        return jsonify({"error": "User not logged in"}), 401
    conn = sqlite3.connect("user_data.db", check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT strftime('%Y-%m-%d', Like_Date_Time) as like_date, Rating FROM Likes"
    )

    likes_data = cursor.fetchall()

    ratings_by_date = defaultdict(list)

    for like_entry in likes_data:
        ratings_by_date[like_entry[0]].append(like_entry[1])

    average_ratings = {
        date: sum(ratings) / len(ratings) for date, ratings in ratings_by_date.items()
    }
    
    formatted_ratings = {
        date: round(rating, 3) for date, rating in average_ratings.items()
    }
    
    if "email" in session:
        email = session["email"]
        conn = sqlite3.connect("user_data.db", check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute("SELECT creator_id FROM creator WHERE email = ?", (email,))
        creator_ids = cursor.fetchall()

    title_count = 0
    album_name_count = 0
    for creator_id in creator_ids:
        cursor.execute(
            "SELECT COUNT(title) FROM uploadsong WHERE creator_id = ?", creator_id
        )

        title_count = cursor.fetchone()[0]

    creator_id = creator_ids[0]
    cursor.execute("SELECT * FROM uploadsong WHERE creator_id = ?", creator_id)
    songs = cursor.fetchall()
    cursor.execute("SELECT * FROM Albums WHERE Album_ID = ?", creator_id)
    albums = cursor.fetchall()

    for creator_id in creator_ids:
        cursor.execute(
            "SELECT album_id FROM uploadsong WHERE creator_id = ?", creator_id
        )

        album_ids = cursor.fetchall()

        for album_id in album_ids:
            cursor.execute(
                "SELECT COUNT(Album_name) FROM Albums WHERE Album_ID = ?", album_id
            )

            album_name_count = cursor.fetchone()[0]

    songs = [song for song in songs]
    albums = [album for album in albums]

    data = {
        "dates": list(formatted_ratings.keys()),
        "ratings": list(formatted_ratings.values()),
        "title_count": title_count,
        "album_count": album_name_count,
        "songs": songs,
        "albums": albums,
    }

    return jsonify(data)

@app.route("/uploads/<filename>", methods=["GET"])
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/useraccount", methods=["GET"])
def useraccount():
    cursor.execute(
        "SELECT name, username, email FROM user WHERE username = ?",
        (session["username"],),
    )
    user_data = cursor.fetchone()

    return render_template("useraccount.html", user_data=user_data)

@app.route("/search", methods=["POST"])
def search():
    if request.method == "POST":
        #we have to check for all possible matches in all songs, albums, playlists, genres and display results accordingly to home.html
        search = request.form["search"]
        cursor.execute(

            "SELECT * FROM uploadsong WHERE title LIKE ? OR artist LIKE ?",
            ("%" + search + "%", "%" + search + "%"),
        )

        songs = cursor.fetchall()
        songs = [song for song in songs]
        cursor.execute(
            "SELECT * FROM Albums WHERE Album_name LIKE ?",
            ("%" + search + "%",),
        )
        albums = cursor.fetchall()
        albums = [album for album in albums]
        cursor.execute(
            "SELECT * FROM Playlists WHERE name LIKE ?",
            ("%" + search + "%",),
        )
        playlists = cursor.fetchall()
        playlists = [playlist for playlist in playlists]
        cursor.execute(
            "SELECT DISTINCT genre FROM uploadsong WHERE genre LIKE ?",
            ("%" + search + "%",),
        )
        genres = cursor.fetchall()
        genres = [genre[0] for genre in genres]
        # print(genres)
        # print(songs)
        print(albums)

        push_search_song_results(songs)
        push_search_album_results(albums)

        return render_template(
            "home.html",
            data=songs,
            album_data=albums,
            genre_data=genres,
            playlists=playlists,
        )
    
def push_search_album_results(albums):
    # Assuming 'albums' is a list of tuples:
    for album_index, album_data in enumerate(albums):
        
        album_key = f"album:{album_data[0]}"
        artist_id = album_data[1]
        album_name = album_data[2]
        release_date = album_data[3]

        
        album_info = {
            "artist_id": artist_id,
            "album_name": album_name,
            "release_date": release_date,
        }
        print(album_info)
        # redis_client.hmset(album_key, album_info)



def push_search_song_results(songs):
    for song in enumerate(songs):
        key = f"song:{song[0]}"
        title = song[1]
    
        song_key = key
        song_data = {
            "name": song[1],
            "artist": song[2],
            "genre": song[3],
            "duration": song[4],
            "date_added": song[5],
            "filename": song[6],
        }
        # redis_client.hmset(song_key, song_data)

  
    
    

@app.route("/adminsearch", methods=["POST"])
# def adminsearch():
#     search = request.form["adminsearch"]
#     # we want to exclude those songs from this adminflag.html template which are not similar to my search query, so code will be same as tracklist route

#     cursor.execute(
#         "SELECT DISTINCT genre FROM uploadsong WHERE title LIKE ? OR artist LIKE ?",
#         ("%" + search + "%", "%" + search + "%"),
#     )
#     genres = cursor.fetchall()
#     genres = [genre[0] for genre in genres]

#     genre_songs = {}
#     for genre in genres:
#         cursor.execute(
#             "SELECT * FROM uploadsong WHERE genre = ? AND title LIKE ? OR artist LIKE ?",
#             (genre, "%" + search + "%", "%" + search + "%"),
#         )
#         songs = cursor.fetchall()
#         songs = [song for song in songs]
#         genre_songs[genre] = songs

#     return render_template("adminflag.html", genresnsongs=genre_songs)


@app.route("/play/<id>", methods=["GET", "POST"])
def play(id):
    if request.method == "GET":
        cursor.execute("SELECT * FROM uploadsong WHERE uploadsong_id = ?", (id,))
        data = cursor.fetchone()
        if "username" in session:
            username = session["username"]
            cursor.execute(
                "SELECT rating FROM Likes WHERE username = ? AND uploadsong_id = ?",
                (username, id),
            )
            rating = cursor.fetchone()
            if rating is not None:
                rating = rating[0]
                return render_template("lyricsnplay.html", data=data, rating=rating)
            else:
                return render_template("lyricsnplay.html", data=data)
    else:
        print("Received rating data from client")
        rating = request.form["rate"]
        print(f"Received rating: {rating}")
        # save this to database if present already by this user then update else insert
        if "username" in session:
            username = session["username"]
            cursor.execute(
                "SELECT rating FROM Likes WHERE username = ? AND uploadsong_id = ?",
                (username, id),
            )
            rating_data = cursor.fetchone()
            if rating_data is None:
                # i want to insert rating, uploadsong_id, username and like_date_time(which will be current date and time)
                cursor.execute(
                    "INSERT INTO Likes (rating, uploadsong_id, username, Like_Date_Time) VALUES (?, ?, ?, datetime('now'))",
                    (rating, id, username),
                )
                conn.commit()
            else:
                # i want to update rating and like_date_time(which will be current date and time)
                cursor.execute(
                    "UPDATE Likes SET rating = ?, Like_Date_Time = datetime('now') WHERE username = ? AND uploadsong_id = ?",
                    (rating, username, id),
                )
                conn.commit()
            return redirect("/play/" + id)
    return jsonify(data=data)


# from functools import wraps


# Define a decorator to check if the user is an admin
# def admin_required(route_function):
#     @wraps(route_function)
#     def wrapper(*args, **kwargs):
#         # Check if 'isAdmin' is present in the session and is equal to 1
#         print(isAdmin)
#         if session.get("isAdmin") == 1:
#             return route_function(*args, **kwargs)
#         else:
#             # Redirect to loginuser.html if not an admin
#             return redirect("/loginuser")

#     return wrapper


@app.route("/admin", methods=["GET"])
def admin():
    is_admin = session.get("isAdmin")
    print(is_admin)

    # If 'isAdmin' is not present or is not equal to 1, return a JSON response indicating unauthorized access
    if is_admin is None or is_admin != 1:
        return jsonify({"error": "Unauthorized access"})

    current_date = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        "SELECT genre, COUNT(*) as genre_count FROM uploadsong WHERE date <= ? GROUP BY genre",
        (current_date,),
    )
    genre_counts = cursor.fetchall()

    cursor.execute(
        "SELECT COUNT(DISTINCT genre) as total_genres FROM uploadsong WHERE date <= ?",
        (current_date,),
    )
    total_genres = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) as total_filenames FROM uploadsong")
    total_filenames = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(DISTINCT album_id) as total_albums FROM Albums",
    )
    total_albums = cursor.fetchone()[0]

    print(total_filenames, total_albums)

    print(total_genres)

    cursor.execute(
        "SELECT genre, date, COUNT(*) as genre_count FROM uploadsong WHERE date <= ? GROUP BY genre, date",
        (current_date,),
    )
    genre_day_counts = cursor.fetchall()
    print(genre_day_counts)

    genre_counts = {}
    for entry in genre_day_counts:
        genre = entry[0]
        count = entry[2]

        if genre not in genre_counts:
            genre_counts[genre] = count
        else:
            genre_counts[genre] += count

    for genre, count in genre_counts.items():
        print(f"{genre}: {count}")
    sorted_genre_counts = dict(sorted(genre_counts.items()))

    chart_categories = list(sorted_genre_counts.keys())
    chart_data = list(sorted_genre_counts.values())

    current_year = datetime.now().strftime("%Y")
    months = [str(i).zfill(2) for i in range(1, 13)]

    filename_counts = {}
    album_counts = {}

    for month in months:
        cursor.execute(
            "SELECT COUNT(*) as filename_count FROM uploadsong WHERE strftime('%Y-%m', date) = ?",
            (f"{current_year}-{month}",),
        )
        filename_counts[month] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) as album_count FROM Albums WHERE strftime('%Y-%m', Release_Date) = ?",
            (f"{current_year}-{month}",),
        )
        album_counts[month] = cursor.fetchone()[0]

    filename_data = list(filename_counts.values())
    album_data = list(album_counts.values())

    today_date = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        """
        SELECT uploadsong_id
        FROM Likes
        WHERE strftime('%Y-%m-%d', Like_Date_Time) = ? 
        ORDER BY Rating DESC
        LIMIT 10
        """,
        (today_date,),
    )

    top_ratings_ids = cursor.fetchall()
    print("top rating ids")
    print(top_ratings_ids)

    uploadsong_ids = [row[0] for row in top_ratings_ids]

    cursor.execute(
        """
        SELECT title
        FROM uploadsong
        WHERE uploadsong_id IN ({})
        """.format(
            ", ".join("?" for _ in uploadsong_ids)
        ),
        uploadsong_ids,
    )

    titles = cursor.fetchall()

    for i, title in enumerate(titles, start=1):
        print(f"{i}. {title[0]}")

    cursor.execute("SELECT COUNT(*) FROM user")
    user_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM creator")
    creator_count = cursor.fetchone()[0]

    print(f"User Count: {user_count}")
    print(f"Creator Count: {creator_count}")

    # Construct a dictionary with the data you want to return
    data = {
        "filename_counts": filename_counts,
        "album_counts": album_counts,
        "user_count": user_count,
        "creator_count": creator_count,
        "chart_categories": chart_categories,
        "chart_data": chart_data,
        "total_genres": total_genres,
        "total_filenames": total_filenames,
        "total_albums": total_albums,
        "top_ratings_titles": [title[0] for title in titles],
    }

    # Return the data as a JSON response
    return jsonify(data)

@app.route("/tracklist", methods=["GET", "POST"])
def tracklist():
    if request.method == "GET":
        if "email" not in session:
            return jsonify({"error": "User not logged in"}), 401
        conn = sqlite3.connect("user_data.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT genre FROM uploadsong")
        genres = cursor.fetchall()
        genres = [genre[0] for genre in genres]
        
        genre_songs = {}
        for genre in genres:
            cursor.execute("SELECT * FROM uploadsong WHERE genre = ?", (genre,))
            songs = cursor.fetchall()
            songs = [song for song in songs]
            print(songs)
            print("\n")
            genre_songs[genre] = songs

        print(genre_songs)
        # Use jsonify to convert the dictionary to JSON format
        return jsonify(genre_songs)


# @app.route("/flagunflag/<id>", methods=["GET", "POST"])
# def flagunflag(id):
#     if request.method == "GET":
#         cursor.execute(
#             "SELECT isFlagged FROM uploadsong WHERE uploadsong_id = ?", (id,)
#         )
#         isFlagged = cursor.fetchone()
#         if isFlagged is not None:
#             isFlagged = isFlagged[0]
#             if isFlagged == 0:
#                 cursor.execute(
#                     "UPDATE uploadsong SET isFlagged = 1 WHERE uploadsong_id = ?", (id,)
#                 )
#                 conn.commit()
#                 return redirect("/tracklist")
#             else:
#                 cursor.execute(
#                     "UPDATE uploadsong SET isFlagged = 0 WHERE uploadsong_id = ?", (id,)
#                 )
#                 conn.commit()
#                 return redirect("/tracklist")
#         else:
#             return redirect("/tracklist")
#     return redirect("/tracklist")


# @app.route("/delete/<id>", methods=["GET", "POST"])
# def delete(id):
#     if request.method == "GET":
#         cursor.execute("DELETE FROM uploadsong WHERE uploadsong_id = ?", (id,))
#         conn.commit()
#         return redirect("/tracklist")
#     return redirect("/tracklist")

@app.route("/flagunflag/<id>", methods=["GET", "POST"])
def flagunflag(id):
    if request.method == "GET":
        cursor.execute(
            "SELECT isFlagged FROM uploadsong WHERE uploadsong_id = ?", (id,)
        )
        is_flagged = cursor.fetchone()
        if is_flagged is not None:
            is_flagged = is_flagged[0]
            if is_flagged == 0:
                cursor.execute(
                    "UPDATE uploadsong SET isFlagged = 1 WHERE uploadsong_id = ?", (id,)
                )
                conn.commit()
                return jsonify({"message": "Song flagged"})
            else:
                cursor.execute(
                    "UPDATE uploadsong SET isFlagged = 0 WHERE uploadsong_id = ?", (id,)
                )
                conn.commit()
                return jsonify({"message": "Flag removed"})
        else:
            return jsonify({"message": "Song not found"}), 404
    return jsonify({"message": "Invalid request method"}), 405

@app.route("/delete/<id>", methods=["DELETE"])
def delete(id):
    if request.method == "DELETE":
        cursor.execute("DELETE FROM uploadsong WHERE uploadsong_id = ?", (id,))
        conn.commit()
        return jsonify({"message": "Song deleted"})
    return jsonify({"message": "Invalid request method"}), 405



if __name__ == "__main__":
    app.run(debug=True)
