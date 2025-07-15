from flask import Flask, request, send_file
import json
import pymysql
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

timeout = 10
conn = pymysql.connect(
  charset="utf8mb4",
  connect_timeout=timeout,
  cursorclass=pymysql.cursors.DictCursor,
  db="defaultdb",
  host=os.getenv("MYSQL_HOST"),
  password=os.getenv("MYSQL_PASSWORD"),
  read_timeout=timeout,
  port=int(os.getenv("MYSQL_PORT")),
  user=os.getenv("MYSQL_USER"),
  write_timeout=timeout,
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    link VARCHAR(100),
    type INT,
    expect INT,
    result INT,
    response VARCHAR(1000)
)
""")

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def home():
    return send_file("../web/dist/index.html")

@app.route("/assets/<path:filename>", methods=["GET"])
def send(filename):
    return send_file("../web/dist/assets/" + filename)

@app.route("/list", methods=["GET"])
def list():
    cursor.execute("SELECT * FROM links")
    rows = cursor.fetchall()
    return json.dumps({ "result": "true", "data": rows }), 200

@app.get("/edit", methods=["GET", "POST"])
def edit():
    if request.method == "GET":
        return send_file("../web/dist/index.html")
    
    try:
        data = request.get_json()
        id = data["id"]
        if (data["type"] == "get"):
            cursor.execute("SELECT * FROM links WHERE id=%s", (id))
            rows = cursor.fetchall()
            return json.dumps({ "result": "true", "data": rows }), 200
        else:
            expect = data["expect"]
            cursor.execute("UPDATE links SET expect=%s WHERE id=%s", (expect, id))
            conn.commit()
            return json.dumps({ "results": "true"})
    except Exception as e:
        print(e)
        return json.dumps({ "result": "false" }), 200

@app.route("/insert", methods=["GET", "POST"])
def insert():
    if request.method == "GET":
        return send_file("../web/dist/index.html")
    
    try: 
        data = request.get_json()
        link = data["link"]
        tipo = int(data["type"])
        expect = int(data["expect"])
        cursor.execute("INSERT INTO links (link, type, expect, result, response) VALUES (%s, %s, %s, %s, %s)", (link, tipo, expect, 2, ""))
        conn.commit()
        return json.dumps({ "result": "true" }), 200
    except Exception as e:
        print(e)
        return json.dumps({ "result": "false" }), 200

@app.route("/delete", methods=["POST"])
def delete():
    data = request.get_json()
    id = int(data["id"])
    cursor.execute("DELETE FROM links WHERE id = %s", (id))
    conn.commit()
    return list()

@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json()
    id_start = data["id_start"]
    id_end = data["id_end"]
    cursor.execute("SELECT * FROM links WHERE id >= %s AND id <= %s", (id_start, id_end))
    rows = cursor.fetchall()

    data = {
        "VERIFY_TOKEN": os.getenv("VERIFY_TOKEN"),
    }

    for row in rows:
        data["link"] = row["link"]

        response = requests.post("http://127.0.0.1:5000/verify", json=data).json()

        verify_result = 1 if "fato" in response["response"][:10] else 0
        response[str(row["id"])] = { "result": verify_result, "response": response["response"] }

        cursor.execute("UPDATE links SET result = %s, response = %s WHERE id = %s", (verify_result, response["response"], int(row["id"])))
        conn.commit()

    return list()

if __name__ == "__main__":
    app.run("0.0.0.0", 12345)

# https://verifai-8z3i.onrender.com