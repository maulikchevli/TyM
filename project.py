import os
import time
import calendar
import datetime
from flask_paginate import Pagination, get_page_parameter
import sqlite3 as sql
from functools import wraps
from flask import Flask,render_template,request,redirect,url_for,session,flash
from passlib.apps import custom_app_context as passHash
from werkzeug import secure_filename
import numpy
import matplotlib.pyplot as plot
import pandas
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn import metrics
import pickle

app = Flask(__name__)
app.secret_key = "super secret key"
UPLOAD_FOLDER = './static/uploads'
PICKLE_FOLDER = './static/pickle'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PICKLE_FOLDER'] = PICKLE_FOLDER

def login_required(f):
	@wraps(f)
	def fn( *args, **kwargs):
		if 'username' not in session:
			session["flashErr"] = "Please login first!"
			return redirect( url_for('login'))
		return f( *args, **kwargs)
	return fn

def dict_factory(cursor,row):
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@app.route('/',methods=['GET'])
def index():
    if request.method == 'GET' :
        logged = False
        username = ""
        pro=False
        if 'username' in session:
            username = session['username']
            logged = True
            if 'user_type' in session:
                if session['user_type'] == "pro":
                    pro=True
        return render_template('index.html',logged=logged,username=username,pro=pro)


@app.route('/login',methods=['POST','GET'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        try:
            password = request.form['password']
            email = request.form['email']

            with sql.connect('database.db') as con:
                con.row_factory = sql.Row
                cur = con.cursor()

                data = cur.execute('SELECT * FROM users WHERE email=?',(email,))
                data = data.fetchall()

                storedPassword = data[0]['password'] #Throws IndexError if no entry is found
                username = data[0]['username']
                user_type=data[0]['user_type']

                if passHash.verify(password,storedPassword):
                        session['username'] = username
                        session['user_type'] = user_type
                        return redirect(url_for('index'))

                else:
                        return render_template('register.html',wrongPassword = True,userNotFound=False)

                con.close()

        except IndexError as es:
            return render_template('login.html',userNotFound = True,wrongPassword=False)


@app.route('/logout')
def logout():
    session.pop('username',None)
    return redirect(url_for('index'))

@app.route('/register',methods = ['POST','GET'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        registered = False
        alreadyUser = False
        try:
            username = request.form['username']
            address = request.form['address']
            fullname = request.form['fullname']
            email = request.form['email']
            password = passHash.hash(request.form['password'])

            with sql.connect("database.db") as con:
                con.row_factory = dict_factory
                cur = con.cursor()

                print("hello")
                cur.execute("SELECT * FROM users WHERE username=? OR email=?",(username,email))
                users = cur.fetchall()
                print("hello")

                if users:
                    print("already exists")
                    registered = False
                    alreadyUser = True
                else:
                    print("inserting")
                    cur.execute("INSERT INTO users (fullname,address,username,email,password) VALUES (?,?,?,?,?)",(fullname,address,username,email,password))
                    print("inserted")
                    con.commit()
                    print("comitted")
                    msg = "Record successfully added"
                    print(msg)
                    uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'],username)
                    pickle_dir = os.path.join(app.config['PICKLE_FOLDER'],username)
                    os.mkdir(uploads_dir)
                    os.mkdir(pickle_dir)
                    registered = True
                    alreadyUser = False
        except:
            print("Error")
            con.rollback()
            msg = "Error in insert operation"

        finally:
            con.close()
            if registered:
                    session['username'] = username
                    session['user_type'] = "std"
                    return redirect(url_for('index'))

            elif alreadyUser:
                    return redirect(url_for('index'))

@app.route('/test_model/<model_id>', methods=['POST', 'GET'])
def test_model(model_id):
	if request.method == 'GET':
		username = session['username']
		with sql.connect("database.db") as con:
			con.row_factory = dict_factory
			cur = con.cursor()
			cur.execute("SELECT * FROM ml_models WHERE id=?",(model_id,))
			model = cur.fetchone()
		return render_template('test_model.html', model=model)
	else:
		file = request.files['test_data']
		with sql.connect("database.db") as con:
			con.row_factory = dict_factory
			cur = con.cursor()
			cur.execute("SELECT * FROM ml_models WHERE id=?",(model_id,))
			model = cur.fetchone()
		accuracy = TestModelFunction(model['filename'],file)
		model['accuracy'] = accuracy
		return render_template('test_result.html',model=model)

@app.route('/model_choice',methods = ['POST','GET'])
@login_required
def model_choice():
    if request.method == "GET":
        return render_template('model_choice.html')
    else:
        model_choice = request.form["model_choice"]
        if model_choice == "regression":
            return render_template('regression_choice.html')
        elif model_choice == "classification":
            return render_template('classification_choice.html')
        else:
            return render_template('clustering_choice.html')


@app.route('/regression_choice',methods = ['POST','GET'])
def regression_choice():
    if request.method == "GET":
        return render_template('regression_choice.html')
    else:
        regression_choice = request.form["regression_choice"]
        if regression_choice == "linear_regression":
            return render_template('linear_regression_parameters.html')

@app.route('/classification_choice',methods = ['POST','GET'])
def classification_choice():
    if request.method == "GET":
        return render_template('classification_choice.html')
    else:
        classification_choice = request.form['classification_choice']
        if classification_choice == "logistic_regression":
            return render_template('logistic_regression_parameters.html')

@app.route('/clustering_choice',methods = ['POST','GET'])
def clustering_choice():
    if request.method == "GET":
        return render_template('clustering_choice.html')
    else:
        clustering_choice = request.form['clustering_choice']
        if clustering_choice == "k_means":
            return render_template('k_means_parameters.html')

@app.route('/linear_regression_parameters',methods=['POST','GET'])
def linear_regression_parameters():
    if request.method == "GET":
        return render_template('linear_regression_parameters.html')
    else:
        file = request.files['training_data']
        model_name = request.form['model_name']
        if file:
            ts = calendar.timegm(time.gmtime())
            filename = secure_filename(file.filename)
            temp_index=filename.find(".")
            temp_filename=filename[0:temp_index]
            extension=filename[temp_index:]
            filename=temp_filename+str(ts)+extension
            uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'],session['username'])
            file.save(os.path.join(uploads_dir,filename))
            model_filename = LinearRegressionImplementation(model_name,filename)
            return redirect(url_for('index'))

def LinearRegressionImplementation(model_name,file):
    model_algo = "linear_regression"
    uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'],session['username'])
    dataset = pandas.read_csv(os.path.join(uploads_dir,file))
    x = dataset.iloc[:, :-1].values
    y = dataset.iloc[:, -1].values
    linearRegressor = LinearRegression()
    linearRegressor.fit(x, y)
    ts = calendar.timegm(time.gmtime())
    model_filename = model_name+str(ts) + '.sav'
    pickle_dir = os.path.join(app.config['PICKLE_FOLDER'],session['username'])
    pickle.dump(linearRegressor, open((os.path.join(pickle_dir,model_filename)), 'wb'))
    y_pred = linearRegressor.predict(x)
    pm = metrics.mean_absolute_error(y, y_pred)
    print('Mean Absolute Error:', pm)
    print('Mean Squared Error:', metrics.mean_squared_error(y, y_pred))
    print('Root Mean Squared Error:', numpy.sqrt(metrics.mean_squared_error(y, y_pred)))
    with sql.connect("database.db") as con:
        con.row_factory = dict_factory
        cur = con.cursor()
        cur.execute("INSERT INTO ml_models (username,model_name,model_algo,filename,performance_measure) VALUES (?,?,?,?,?)",(session['username'],model_name,model_algo,model_filename,str(pm)))
        con.commit()
    return model_filename


def TestModelFunction(pickle_filename,file):
    model_algo = "linear_regression"
    dataset = pandas.read_csv(file)
    x = dataset.iloc[:, :-1].values
    y = dataset.iloc[:, -1].values
    pickle_dir = os.path.join(app.config['PICKLE_FOLDER'],session['username'])
    pickle_file= os.path.join(pickle_dir,str(pickle_filename))
    f = open(pickle_file,"rb")
    pickle_model = pickle.load(f)
    return pickle_model.score(x,y)

@app.route('/history')
def history():
    username = session['username']
    with sql.connect("database.db") as con:
        con.row_factory = dict_factory
        cur = con.cursor()
        cur.execute("SELECT * FROM ml_models WHERE username=?",(username,))
        models = cur.fetchall()
        print(models)
        return render_template('history.html',models=models)


@app.route('/model_info/<model_id>')
def model_info(model_id):
        username = session['username']
        with sql.connect("database.db") as con:
                con.row_factory = dict_factory
                cur = con.cursor()
                cur.execute("SELECT * FROM ml_models WHERE id=?",(model_id,))
                model = cur.fetchone()
        return render_template('model_info.html', model=model)


@app.route('/logistic_regression_parameters',methods=['POST','GET'])
@login_required
def logistic_regression_parameters():
    if request.method == "GET":
        return render_template('logistic_regression_parameters.html')
    else:
        file = request.files['training_data']
        model_name = request.form['model_name']
        max_iter = request.form['max_iter']
        if file:
            ts = calendar.timegm(time.gmtime())
            filename = secure_filename(file.filename)
            temp_index=filename.find(".")
            temp_filename=filename[0:temp_index]
            extension=filename[temp_index:]
            filename=temp_filename+str(ts)+extension
            uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'],session['username'])
            file.save(os.path.join(uploads_dir,filename))
            model_filename = LogisticRegressionImplementation(model_name,filename,int(max_iter))
            return redirect(url_for('index'))

def LogisticRegressionImplementation(model_name,file,max_iter):
    model_algo = "logistic_regression"
    uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'],session['username'])
    dataset = pandas.read_csv(os.path.join(uploads_dir,file))
    x = dataset.iloc[:, :-1].values
    y = dataset.iloc[:, -1].values
    print(y)
    classifier = LogisticRegression(max_iter=max_iter)
    classifier.fit(x, y)
    ts = calendar.timegm(time.gmtime())
    model_filename = model_name+str(ts) + '.sav'
    pickle_dir = os.path.join(app.config['PICKLE_FOLDER'],session['username'])
    pickle.dump(classifier, open((os.path.join(pickle_dir,model_filename)), 'wb'))
    y_pred = classifier.predict(x)
    pm = metrics.accuracy_score(y, y_pred)
    print("Accuracy:",pm)
    with sql.connect("database.db") as con:
        con.row_factory = dict_factory
        cur = con.cursor()
        cur.execute("INSERT INTO ml_models (username,model_name,model_algo,filename,performance_measure) VALUES (?,?,?,?,?)",(session['username'],model_name,model_algo,model_filename,str(pm)))
        con.commit()
    return model_filename

@app.route('/k_means_parameters',methods=['POST','GET'])
@login_required
def k_means_parameters():
    if request.method == "GET":
        return render_template('k_means_parameters.html')
    else:
        file = request.files['training_data']
        model_name = request.form['model_name']
        max_iter = request.form['max_iter']
        n_clusters = request.form['n_clusters']
        if file:
            filename = secure_filename(file.filename)
            uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'],session['username'])
            file.save(os.path.join(uploads_dir,filename))
            model_filename = KMeansImplementation(model_name,filename,int(max_iter),int(n_clusters))
            return redirect(url_for('index'))

def KMeansImplementation(model_name,file,max_iter,n_clusters):
    model_algo = "k_means"
    uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'],session['username'])
    dataset = pandas.read_csv(os.path.join(uploads_dir,file))
    X = dataset.iloc[:, :-1].values
    X = pandas.DataFrame(X)
    X = X.convert_objects(convert_numeric=True)

    for i in X.columns:
        X[i] = X[i].fillna(int(X[i].mean()))
    for i in X.columns:
        print(X[i].isnull().sum())

    kmeans = KMeans(n_clusters=n_clusters,init='k-means++',max_iter=max_iter,n_init=10,random_state=0)
    kmeans.fit(X)
    model_filename = model_name + '.sav'
    pickle_dir = os.path.join(app.config['PICKLE_FOLDER'],session['username'])
    pickle.dump(kmeans, open((os.path.join(pickle_dir,model_filename)), 'wb'))
    pm = "NA"
    with sql.connect("database.db") as con:
        con.row_factory = dict_factory
        cur = con.cursor()
        cur.execute("INSERT INTO ml_models (username,model_name,model_algo,filename,performance_measure) VALUES (?,?,?,?,?)",(session['username'],model_name,model_algo,model_filename,pm))
        con.commit()
    return model_filename


if __name__ == "__main__":
    app.run(debug=True)
