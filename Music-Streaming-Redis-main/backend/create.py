import sqlite3

conn = sqlite3.connect("user_data.db")
cursor = conn.cursor()

# -------- user login register ---------
# sql_query = """CREATE TABLE user(
# name text,
# username text,
# email text  PRIMARY KEY,
# password text,
# isAdmin int
# )"""


# --------- admin login register----------
# sql_query = """CREATE TABLE admin(
# name text,
# username text PRIMARY KEY,
# email text,
# password text,
# isAdmin int
# )"""


# -------upload song ---------
# duration is in seconds

# sql_query = """
# CREATE TABLE uploadsong(
#     uploadsong_id INTEGER PRIMARY KEY AUTOINCREMENT,
#     title TEXT,
#     artist TEXT,
#     genre TEXT,
#     duration INT,
#     date TEXT,
#     filename TEXT,
#     lyrics TEXT,
#     isFlagged INT,
#     creator_id INTEGER,
#     album_id INTEGER,
#     FOREIGN KEY (creator_id) REFERENCES creator(creator_id),
#     FOREIGN KEY (album_id) REFERENCES album(album_id)
# )
# """


# -------- creator table -----

# sql_query = """CREATE TABLE creator(
# creator_id INTEGER PRIMARY KEY AUTOINCREMENT,
# artist text,
# email text,
# genre text
# )"""

# -------- album table ------------

# sql_query = """CREATE TABLE Albums (
#   Album_ID INTEGER PRIMARY KEY AUTOINCREMENT,
#   Artist_ID INTEGER,
#   Album_name TEXT NOT NULL,
#   Release_Date DATE,
#   FOREIGN KEY (Artist_ID) REFERENCES Artists(Artist_ID)
# )"""


# ----------- playlists ----------

# sql_query = """CREATE TABLE Playlists (
#   Playlist_ID INTEGER PRIMARY KEY AUTOINCREMENT,
#   username TEXT,
#   Name TEXT NOT NULL,
#   FOREIGN KEY (username) REFERENCES user(username)
# )
# """

# --------- playlists-track table -------

# sql_query = """CREATE TABLE Playlist_Tracks (
#   Playlist_ID INT,
#   uploadsong_id INT,
#   FOREIGN KEY (Playlist_ID) REFERENCES Playlists(Playlist_ID),
#   FOREIGN KEY (uploadsong_id) REFERENCES uploadsong(uploadsong_id)
# )"""

# --------- Likes table ---------

# sql_query = """CREATE TABLE Likes (
#   username TEXT,
#   uploadsong_id INT,
#   Rating INT,
#   Like_Date_Time DATETIME,
#   PRIMARY KEY (username, uploadsong_id),
#   FOREIGN KEY (username) REFERENCES user(username),
#   FOREIGN KEY (uploadsong_id) REFERENCES uploadsong(uploadsong_id)
# )"""


# --------- Recent songs ---------

# sql_query = """CREATE TABLE Recent_Songs (
#   uploadsong_id INT,
#   Click_Date_Time DATETIME,
#   PRIMARY KEY (uploadsong_id),
#   FOREIGN KEY (uploadsong_id) REFERENCES uploadsong(uploadsong_id)
# )"""

# cursor.execute("DROP TABLE IF EXISTS Playlist_Tracks")
# to clear all the data
# cursor.execute("DELETE FROM Recent_Songs")

# cursor.execute(sql_query)
# try:
#     cursor.execute(
#         "INSERT INTO Recent_Songs (uploadsong_id, Click_Date_Time) VALUES ('5', '2024-03-19 01:20:31')"
#     )
#     conn.commit()
# except Exception as e:
#     print(f"Error: {e}")
#     conn.rollback()



# sql_insert = """
# INSERT INTO uploadsong (title, artist, genre, duration, date, filename, lyrics, isFlagged, creator_id, album_id)
# VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
# """

# # Define the song details
# song_details = ('Song Title', 'Artist Name', 'Genre', 300, '2024-03-19', 'song.mp3', 'Lyrics here', 0, 1, 1)

# # Execute the INSERT statement with the song details
# cursor.execute(sql_insert, song_details)

# # Commit the transaction to save the changes
# conn.commit()

# # Close the cursor and the connection
# cursor.close()
# conn.close()
conn.commit()
