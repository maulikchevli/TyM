import os
import time
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

app = Flask(__name__)
app.secret_key = "super secret key"
UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


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
        if 'username' in session:
            username = session['username']
            logged = True
        return render_template('index.html',logged=logged,username=username)


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


                if passHash.verify(password,storedPassword):
                        session['username'] = username
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
                    cur.execute("INSERT INTO users (fullname,address,username,email,password) VALUES (?,?,?,?,?)",(fullname,address,username,email,password))
                    con.commit()
                    msg = "Record successfully added"
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
                    return redirect(url_for('index'))

            elif alreadyUser:
                    return redirect(url_for('index'))

@app.route('/model_choice',methods = ['POST','GET'])
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

@app.route('/clustering_choice',methods = ['POST','GET'])
def clustering_choice():
    if request.method == "GET":
        return render_template('clustering_choice.html')

@app.route('/linear_regression_parameters',methods=['POST','GET'])
def linear_regression_parameters():
    if request.method == "GET":
        return render_template('linear_regression_parameters.html')
    else:
        file = request.files['training_data']
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
