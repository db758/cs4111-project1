#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver
To run locally
    python server.py
Go to http://localhost:8111 in your browser
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "db3526"
DB_PASSWORD = "2639"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/proj1part2"

# This line creates a database engine that knows how to connect to the URI above

engine = create_engine(DATABASEURI)

# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request
  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None


@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/


@app.route('/')
def index():
  return render_template("index.html")

@app.route('/search_eatery/', methods = ['POST'])
def search_eatery():
  eatery_name = request.form['search_eatery_name']
  tag = request.form['Tags']
  # 1. Tag
  if (tag != 'Blank' and eatery_name == ""):
    cursor = g.conn.execute('SELECT Eateries.eid, name, is_open, location, is_indoor, hours, e_type, seating, bathroom FROM Contain, Eateries WHERE Contain.label = %s and Contain.eid = Eateries.eid', (tag))
  # 2. Name
  elif (tag == 'Blank' and eatery_name != ""):
    cursor = g.conn.execute('SELECT * FROM Eateries WHERE name LIKE %s', ('%'+eatery_name+'%'))
  # 3. Both
  else:
    try:
      cursor = g.conn.execute('SELECT * FROM Eateries WHERE name LIKE %s JOIN (SELECT * FROM Contains, Eateries WHERE Contain.label = %s and Contain.eid = Eateries.eid) ON eid', ('%'+eatery_name+'%',tag))
    except:
      return render_template("error.html")
  names = []
  headings = ("Eatery name","Is open?","Location","Indoor/Outdoor","Hours","Eatery type","Number of seats","Restrooms")
  #names.append(headings)
  for result in cursor:
    names.append(result[1:])  # can also be accessed using result[0]
  cursor.close()
  if len(names)==0:
    return render_template("error.html")
  context = dict(eateries=names,headings=headings)
  return render_template("index.html", **context)


@app.route('/search_eatery_rating/', methods = ['POST'])
def search_eatery_rating():
  eatery = request.form['search_eatery_rating']
  cursor = g.conn.execute('SELECT eid FROM Eateries WHERE name = %s',(eatery))
  eid = []
  for result in cursor:
    eid.append(result[0])
  if len(eid)==0: 
    return render_template("error.html")
  cursor = g.conn.execute('SELECT AVG(seating), AVG(atmosphere), AVG(natural_lighting) FROM Ratings_About_Submitted WHERE eid=%s', (eid[0]))

  names = []
  ratingc = ("Avg. rating: seating", "Avg. rating: atmosphere", "Avg. rating: natural lighting")
  for result in cursor:
    names.append(result[:3])  


  context = dict(ratings = names, ratingc=ratingc)
  cursor.close()
  return render_template("index.html", **context)

@app.route('/search_eatery_comment/', methods = ['POST'])
def search_eatery_comment():
  eatery = request.form['search_eatery_comment']
  cursor = g.conn.execute('SELECT eid FROM Eateries WHERE name = %s',(eatery))
  eid = []
  for result in cursor:
    eid.append(result[0])
  if len(eid)==0:
    return render_template("error.html")
  cursor = g.conn.execute('SELECT A.content, B.username, A.when_commented FROM Comments_About_C as A, Comments_Submitted_C as B WHERE eid=%s AND A.cid = B.cid', (eid[0]))

  names = []
  commentc = ("Comment", "Username", "Time of comment")
  for result in cursor:
    names.append(result[:3])  

  context = dict(comments = names, commentc=commentc)
  cursor.close()
  return render_template("index.html", **context)

@app.route('/search_eatery_food/', methods = ['POST'])
def search_eatery_food():
  eatery = request.form['search_eatery_food']
  cursor = g.conn.execute('SELECT eid from Eateries WHERE name=%s', (eatery))
  eid = []
  for result in cursor:
    eid.append(result[0])
  if len(eid)==0:
    return render_template("error.html")
  cursor = g.conn.execute('SELECT Items_Sold.name, Items_Sold.price, AVG(Rate.rating) FROM Items_Sold, Rate WHERE Items_Sold.eid = %s AND Items_Sold.eid=Rate.eid AND Items_Sold.iid = Rate.iid GROUP BY Rate.iid, Rate.eid, Items_Sold.name, Items_Sold.price' , (eid[0]))

  names = []
  itemsc = ("Name", "Price", "Average Rating")
  for result in cursor:
    names.append(result[:3])
  context = dict(items = names, itemsc=itemsc)
  cursor.close()
  return render_template("index.html", **context)



@app.route('/add_to_try_list/', methods = ['POST', 'GET'])
def add_to_try_list():
  if request.method == 'GET':
    return render_template("index.html")
  elif request.method == 'POST':
    username = request.form['add_to_try_username']
    cursor = g.conn.execute('SELECT username FROM Users WHERE username=%s', (username))
    usernames = []
    for result in cursor:
      usernames.append(result[0])
    if len(usernames) == 0:
      return render_template("error.html")
    eatery = request.form['add_to_try_eatery']
    cursor = g.conn.execute('SELECT DISTINCT tid FROM To_Try_List WHERE username = %s', (username))
    tid = []
    for result in cursor:
      tid.append(result[0])
    if len(tid)==0:
      cursor = g.conn.execute('SELECT MAX(tid)+1 FROM To_Try_List')
      newtid = []
      for result in cursor:
        newtid.append(result[0])
      cursor = g.conn.execute('SELECT eid FROM Eateries WHERE name = %s',(eatery))
      eid = []
      for result in cursor:
        eid.append(result[0])
      if len(eid) == 0:
        return render_template("error.html")
      cursor = g.conn.execute('INSERT INTO To_Try_List VALUES (%s, %s, %s)',(newtid[0],eid[0], username))
    else:
      cursor = g.conn.execute('SELECT eid FROM Eateries WHERE name = %s',(eatery))
      eid = []
      for result in cursor:
        eid.append(result[0])
      if len(eid) == 0:
        return render_template("error.html")
      cursor = g.conn.execute('INSERT INTO To_Try_List VALUES (%s, %s, %s)',(tid[0],eid[0], username))
    cursor.close()
    return redirect("/")#render_template("index.html")

@app.route('/add_item/', methods = ['POST']) 
def add_item():
  item = request.form['add_item_food']
  eatery = request.form['add_item_eatery']
  price = request.form['add_item_price']
  cursor = g.conn.execute('SELECT DISTINCT eid FROM Eateries WHERE name = %s', (eatery))
  eid = []
  for result in cursor:
    eid.append(result[0])
  if len(eid)==0: 
    return render_template("error.html")
  cursor = g.conn.execute('SELECT MAX(iid)+1 FROM Items_Sold WHERE eid = %s', (eid[0]))
  iid = []
  for result in cursor:
    iid.append(result[0])
  if iid[0] == None:
    iid[0] = 1  
  try:
    cursor = g.conn.execute('INSERT INTO Items_Sold VALUES (%s, %s, %s, %s)',(iid[0],price,item,eid[0]))
    cursor.close()
    return redirect("/") #render_template("index.html")
  except:
    return render_template("error.html")

@app.route('/rate_item/', methods = ['POST', 'GET'])
def rate_item():
  if request.method == 'GET':
    return render_template("index.html")
  else:
    item = request.form['rate_item_food']
    eatery = request.form['rate_item_eatery']
    rating = request.form['rate_item_rating']
    if rating == 'Blank':
      return render_template("error.html")
    username = request.form['rate_item_username']
    cursor = g.conn.execute('SELECT username FROM Users WHERE username=%s', (username))
    usernames = []
    for result in cursor:
      usernames.append(result[0])
    if len(usernames) ==0:
      return render_template("error.html")
    cursor = g.conn.execute('SELECT DISTINCT eid FROM Eateries WHERE name = %s', (eatery))
    eid = []
    for result in cursor:
      eid.append(result[0])
    if len(eid)==0: 
      return render_template("error.html")
    else:
      cursor = g.conn.execute('SELECT iid FROM Items_Sold WHERE eid = %s AND name = %s', (eid[0], item))
      iid = []
      for result in cursor:
        iid.append(result[0])
      if len(iid)==0:
        return render_template("error.html")
      else:
        try:
          cursor = g.conn.execute('INSERT INTO Rate VALUES (%s, %s, %s, %s)', (username, eid[0], iid[0], rating))
          # need to check for uniqueness
          cursor.close()
          return redirect("/")
        except:
          return render_template("error.html")

@app.route('/rate_eatery/', methods = ['POST'])
def rate_eatery():
  username = request.form['rate_eatery_username']
  eatery = request.form['rate_eatery_eatery']
  bg_noise = request.form['rate_background_noise']
  bg_music = request.form['rate_background_music']
  seating = request.form['rate_seating']
  atmosphere = request.form['rate_atmosphere']
  lighting = request.form['rate_natural_lighting']
  cursor = g.conn.execute('SELECT DISTINCT eid FROM Eateries WHERE name = %s', (eatery))
  eid = []
  for result in cursor:
    eid.append(result[0])
  if len(eid)==0: 
    return render_template("/")
  cursor = g.conn.execute('INSERT INTO Ratings_About_Submitted VALUES (DEFAULT, %s, %s, %s, %s, %s, %s, %s)', (bg_noise, bg_music, seating, atmosphere, lighting, eid[0], username))
  cursor.close()
  return redirect("/") #render_template("index.html")

@app.route('/comment_eatery/', methods = ['POST'])
def comment_eatery():
  username = request.form['comment_eatery_username']
  eatery = request.form['comment_eatery_eatery']
  content = request.form['comment_eatery_comment']
  cursor = g.conn.execute('SELECT DISTINCT eid FROM Eateries WHERE name = %s', (eatery))
  eid = []
  for result in cursor:
    eid.append(result[0])
  if len(eid)==0: 
    return render_template("/")
  cursor = g.conn.execute('SELECT MAX(cid)+1 FROM Comments_Submitted_C')
  newcid = []
  for result in cursor:
    newcid.append(result[0])
  cid = newcid[0]
  cursor = g.conn.execute('INSERT INTO Comments_Submitted_C VALUES (%s, %s, DEFAULT, %s)', (cid, content, username))
  cursor = g.conn.execute('INSERT INTO Comments_About_C VALUES (%s, %s, DEFAULT, %s)', (cid, content, eid[0]))
  cursor.close()
  return redirect("/")#render_template("index.html")


@app.route('/search_to_try_list/', methods=['GET','POST'])
def search_to_try_list():
  """
  request is a special object that Flask provides to access web request information:
  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2
  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # GET - when page reloads
  if request.method == 'GET': # runs when reload webpage
    return render_template("index.html") # return default homepage
    # redirects to
  
  # POST method
  if request.method =='POST':
    username = request.form['search_username']
    cursor = g.conn.execute("SELECT Eateries.name FROM Eateries, To_Try_List WHERE To_Try_List.eid = Eateries.eid AND To_Try_List.username = %s", username)
    names = []
    for result in cursor:
      names.append(result['name'])  # can also be accessed using result[0]
    cursor.close()
    if len(names) == 0:
      return render_template("error.html")
    context = dict(data = names)
  return render_template("index.html", **context) # index.html?


@app.route('/add_eatery/', methods=['GET', 'POST'])
def add_eatery():
  
  if request.method == 'GET':
    return render_template("index.html")

  if request.method == 'POST':
    username = request.form['username']
    eatery_name = request.form['eatery_name']
    is_open = request.form['is_open']
    location = request.form['location']
    is_indoor = request.form['is_indoor']
    hours = request.form['hours']
    e_type = request.form['e_type']
    seating = request.form['seating']
    bathroom = request.form['bathroom']

    cursor = g.conn.execute("INSERT INTO Eateries VALUES(DEFAULT, %s, %s, %s, %s, %s, %s, %s, %s)", (eatery_name, is_open, location, is_indoor, hours, e_type, seating, bathroom))
    cursor.close()

    return redirect("/") #render_template("index.html")


@app.route('/add_user/', methods = ['GET', 'POST'])
def add_user():

  if request.method == 'GET':
    return render_template("index.html")

  if request.method == 'POST':
    username = request.form['username']
    affiliation = request.form['affiliation']
    biography = request.form['bio']

    try:
      cursor = g.conn.execute("INSERT INTO Users VALUES(%s, %s, DEFAULT, %s)", (username, affiliation, biography))
      cursor.close()

      return redirect("/") #render_template("index.html")
    except:
      return render_template("error.html")




if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using
        python server.py
    Show the help text using
        python server.py --help
    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()