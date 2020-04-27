import sqlite3
import os
import json

from flask import Flask, flash, escape, request, jsonify, json, g, redirect, url_for, send_from_directory


DATABASE = './assignment2.db'
UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'json'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



#1. Create a test
@app.route('/api/tests', methods = ['POST'])
def createTest():
    temp = request.get_json()
    subject = temp["subject"]
    answersKeys = temp["answer_keys"]
    conn = sqlite3.connect(DATABASE)
    
    #create a table Math to store the answer of Math exam
    sql = "CREATE TABLE IF NOT EXISTS " + subject +  " (answer_key INTEGER PRIMARY KEY, answer_value VARCHAR)"
    cursor = conn.cursor()
    cursor.execute(sql)

    for key in answersKeys:
        value = answersKeys[key]
        sql = "INSERT INTO " + subject + " (answer_key, answer_value) VALUES (" + key + ", '" + value + "')"
        cursor.execute(sql)
        
    #create a table test_id to store the test_id information
    sql = "CREATE TABLE IF NOT EXISTS test_id (id INTEGER PRIMARY KEY AUTOINCREMENT, subject VARCHAR)"
    cursor.execute(sql)
    sql = "INSERT INTO test_id (subject) VALUES ('" + subject + "')"
    cursor.execute(sql)

    query = "SELECT * FROM test_id WHERE subject = '" + subject + "'"
    cursor.execute(query)
    values = cursor.fetchall()
    res = {}
    res["test_id"] = values[0][0]
    res["subject"] = subject
    res["answers_keys"] = answersKeys
    res["submissions"] = []
    conn.commit()
    conn.close()
    return res, 201

def genResult(data):
    subject = data["subject"]
    answers = data["answers"]
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    query = "SELECT * FROM " + subject
    cursor.execute(query)
    values = cursor.fetchall()
    student_score = 0
    result = {}
    for row in values:
        question_id = row[0]
        submitted_answer = answers[str(question_id)]
        correct_answer = row[1]
        tmp = {}
        tmp["actual"] = submitted_answer
        tmp["expected"] = correct_answer
        result[row[0]] = tmp
        if submitted_answer == correct_answer:
            student_score = student_score + 1

    data["result"] = result
    data["score"] = student_score
    conn.commit()
    conn.close()
    return data

def saveScantron(data, path):
    conn = sqlite3.connect(DATABASE)
    sql = "CREATE TABLE IF NOT EXISTS scantron (id INTEGER PRIMARY KEY AUTOINCREMENT, scantron_url VARCHAR, name VARCHAR, subject VARCHAR, answers VARCHAR(1000))"
    cursor = conn.cursor()
    cursor.execute(sql)

    sql = "INSERT INTO scantron (scantron_url, name, subject, answers) VALUES (?, ?, ?, ?)"
    cursor.execute(sql, (path, data["name"], data["subject"], json.dumps(data["answers"])))

    query = "SELECT id FROM scantron WHERE name = ? AND subject = ? AND scantron_url = ?"
    cursor.execute(query, (data["name"], data["subject"], path, ))
    values = cursor.fetchall()
    data["scantron_id"] = values[0][0]
    data["scantron_url"] = path
    output = genResult(data)
    conn.commit()
    conn.close()
    del output["answers"]
    return output
    
def allowed_file(filename):
    return '.' in filename and \
       filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
       
#2. Upload a scantron
@app.route('/api/tests/<test_id>/scantrons', methods = ['POST'])
def uploadScantron(test_id):

    if 'data' not in request.files:
        print ('No file part')
        return redirect(request.url)
    file = request.files['data']
    if file.filename == '':
        print('No selected file')
        return redirect(request.url)
    if allowed_file(file.filename) == False:
        print('File type not allowed')
        return redirect(request.url)
        
    filename = file.filename
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as inPutFile:
        data = json.load(inPutFile)
        path = "http://localhost:5000/uploads/" + filename
        return saveScantron(data, path), 201
        
        
#3. Check all scantron submissions
@app.route('/api/tests/<test_id>', methods = ['GET'])
def checkAll(test_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    query = "SELECT * FROM test_id WHERE id = " + test_id
    cursor.execute(query)
    values = cursor.fetchall()
    subject = values[0][1]
    output = {}
    output["test_id"] = test_id
    output["subject"] = subject

    answer_keys = {}
    query = "SELECT * FROM " + subject
    cursor.execute(query)
    values = cursor.fetchall()
    for row in values:
        answer_keys[row[0]] = row[1]
    output["answer_keys"] = answer_keys
    
    submissions = []
    query = "SELECT * FROM scantron WHERE subject = '" + subject + "'"
    cursor.execute(query)
    values = cursor.fetchall()
    for row in values:
        data = {}
        data["scantron_id"] = row[0]
        data["scantron_url"] = row[1]
        data["name"] = row[2]
        data["subject"] = row[3]
        data["answers"] = json.loads(row[4])
        sub = genResult(data)
        del sub["answers"]
        submissions.append(sub)

    output["submissions"] = submissions
    return output, 200
