from flask import Flask, request, send_file, make_response
import json
import pymysql
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS
import asyncio
import time
from threading import Thread

load_dotenv()

timeout = 10

def get_connection():
    return pymysql.connect(
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


class QuerysQueue:
    queue = {}
    queue2 = {}
    received_values = {}
    is_queue_processing = False
    def __init__(self):
        self.setup()

    def setup(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()
    
    def close(self):
        self.conn.close()

    async def process_queue(self):
        self.is_queue_processing = True

        try:
            for id in self.queue:
                current_queue = self.queue[id]

                if current_queue[1] == "get":
                    self.cursor.execute(*current_queue[0])
                    self.queue[id][0] = self.cursor.fetchall()

                else:
                    self.cursor.execute(*current_queue[0])
                    self.queue[id][0] = self.conn.commit()

                self.received_values[id] = self.queue[id][0]

                self.queue[id][2].set()


            if len(self.queue2) > 0:
                self.queue = self.queue2
                self.queue2 = {}
                await self.process_queue()

            else:
                self.is_queue_processing = False
                self.queue = {}
                self.setup()

        except Exception as e:
            print(e)

            for id in self.queue:
                self.queue[id][2].set()

            if len(self.queue2) > 0:
                self.queue = self.queue2
                self.queue2 = {}
                await self.process_queue()

            else:
                self.is_queue_processing = False
                self.queue = {}
                self.setup()

    async def process_query(self, string: str, type: str):
        id = str(int(time.time() * 1000000))
        event = asyncio.Event()

        if self.is_queue_processing:
            self.queue[id] = [ string, type, event ]
        
        else:
            self.queue2[id] = [ string, type, event ]

        if not self.is_queue_processing:
            asyncio.create_task(self.process_queue())

        await event.wait()

        value = self.received_values[id]
        
        del self.received_values[id]

        return value
    
    def add_get_query(self, *string: str):
        return asyncio.run(self.process_query(string, type="get"))

    def add_modify_query(self, *string: str):
        return asyncio.run(self.process_query(string, type="modify"))
    

queue = QuerysQueue()
# conn = pymysql.connect(
#   charset="utf8mb4",
#   connect_timeout=timeout,
#   cursorclass=pymysql.cursors.DictCursor,
#   db="defaultdb",
#   host=os.getenv("MYSQL_HOST"),
#   password=os.getenv("MYSQL_PASSWORD"),
#   read_timeout=timeout,
#   port=int(os.getenv("MYSQL_PORT")),
#   user=os.getenv("MYSQL_USER"),
#   write_timeout=timeout,
# )

# cursor = conn.cursor()

# cursor.execute("""
# CREATE TABLE IF NOT EXISTS links (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     link VARCHAR(100),
#     type INT,
#     expect INT,
#     result INT,
#     response VARCHAR(2100)
# )
# """)
app = Flask(__name__)
CORS(app, supports_credentials=True)

@app.route("/", methods=["GET"])
def home():
    return send_file("../web/public/index.html")

@app.route("/assets/<path:filename>", methods=["GET"])
def send(filename):
    return send_file("../web/public/assets/" + filename)

# rows = queue.add_modify_query("""SET @pos := 0;
# UPDATE links
# JOIN (
#     SELECT id, @pos := @pos + 1 AS nova_ordem
#     FROM links
#     ORDER BY id
# ) AS ordenado
# ON links.id = ordenado.id
# SET links.id = ordenado.nova_ordem""")

# queue.add_modify_query("DROP TABLE links_temp2;")
# rows = queue.add_get_query("SELECT * FROM ( SELECT *, (SELECT COUNT(*) AS n_repeticoes FROM links AS lp WHERE lp.link = la.link) AS n_repeticoes FROM links AS la ) AS sub WHERE n_repeticoes > 1")
# print(rows)
# rows = queue.add_modify_query("""DELETE l1
# FROM links l1
# JOIN (
#     SELECT link, MAX(id) AS max_id
#     FROM links
#     GROUP BY link
#     HAVING COUNT(*) > 1
# ) AS sub ON l1.link = sub.link AND l1.id = sub.max_id;""")
# queue.add_modify_query("""UPDATE links
# SET link = CASE 
#              WHEN RIGHT(SUBSTRING_INDEX(link, '?', 1), 1) = '/' THEN 
#                LEFT(SUBSTRING_INDEX(link, '?', 1), LENGTH(SUBSTRING_INDEX(link, '?', 1)) - 1)
#              ELSE 
#                SUBSTRING_INDEX(link, '?', 1)
#           END
# WHERE link LIKE '%?%';""")
# queue.add_modify_query("ALTER TABLE links MODIFY response VARCHAR(1500)")
# conn = get_connection()
# try:
#     with conn.cursor() as cursor:
#         cursor.execute("ALTER TABLE links MODIFY ipv6 VARCHAR(50);")
#         rows = conn.commit()
# finally:
#     conn.close()

@app.route("/list", methods=["POST"])
def list():
    data = request.get_json()
    page = data["page"]
    postsPerPage = data["postsPerPage"]
    init_post = page * postsPerPage

    rows = queue.add_get_query(f"SELECT *, (SELECT COUNT(*) FROM links) AS n_posts FROM links ORDER BY id LIMIT {init_post}, {postsPerPage}")
    return json.dumps({ "result": "true", "isAdmin": request.cookies.get("ipv6").startswith("2804:25ac:43c:fd00"), "data": rows }), 200


@app.route("/edit", methods=["GET","POST"])
def edit():
    if request.method == "GET":
        return send_file("../web/public/index.html")
    
    response = None

    try: 
        data = request.get_json()

        type = data["type"]
        id = data["id"]

        if type == "get":
            row = queue.add_get_query("SELECT * FROM links WHERE id=%s", (id,))[0]
            response = json.dumps({ "result": "true", "data": row }), 200

        else:
            tipo = int(data["type"])
            expect = int(data["expect"])
            ipv6 = request.cookies.get("ipv6")
            queue.add_modify_query("UPDATE links SET type=%s, expect=%s, ipv6=%s WHERE id=%s", (tipo, expect, ipv6, id))
            response = json.dumps({ "result": "true" }), 200
        
        return response
    
    except Exception as e:
        print(e)
        return json.dumps({ "result": "false" }), 200

@app.route("/insert", methods=["GET", "POST"])
def insert():
    if request.method == "GET":
        return send_file("../web/public/index.html")
    
    try:
        data = request.get_json()
        link = data["link"]
        if len(queue.add_get_query("SELECT id FROM links WHERE link=%s",(link))) > 0:
            return json.dumps({ "result": "false", "message": "exists" })

        tipo = int(data["type"])
        expect = int(data["expect"])
        ipv6 = request.cookies.get("ipv6")
        timestamp = int(time.time())
        queue.add_modify_query("INSERT INTO links (link, type, expect, result, response, ipv6, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)", (link, tipo, expect, 2, "", ipv6, timestamp))
        return json.dumps({ "result": "true" }), 200
    except Exception as e:
        print(e)
        return json.dumps({ "result": "false" }), 200

@app.route("/delete", methods=["POST"])
def delete():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            data = request.get_json()
            id = int(data["id"])
            cursor.execute("DELETE FROM links WHERE id = %s", (id,))
            conn.commit()
    except Exception as e:
        print(e)
    finally:
        conn.close()
        return list()

@app.route("/verify", methods=["POST"])
def verify():
    conn = get_connection()
    try:
        data = request.get_json()
        id_start = data["id_start"]
        id_end = data["id_end"]
        rows = queue.add_get_query("SELECT * FROM links WHERE id >= %s AND id <= %s", (id_start, id_end))

        data = {
            "VERIFY_TOKEN": os.getenv("VERIFY_TOKEN"),
        }

        for row in rows:
            data["link"] = row["link"]

            response = requests.post("https://6v9s4f5f-5000.brs.devtunnels.ms/verify", json=data).json()
            print(response)
            verify_result = 1 if "fato" in response["response"][:10] else 0
            response[str(row["id"])] = { "result": verify_result, "response": response["response"] }

            queue.add_modify_query("UPDATE links SET result = %s, response = %s WHERE id = %s", (verify_result, response["response"], int(row["id"])))
        
        return list()
    
    except Exception as e:
        print(e)
        conn.close()
        return json.dumps({ "result": "false" }), 200

@app.route("/has_defined")
def has_defined():
    return json.dumps({ "setted": True if request.cookies.get("ipv6") else False }), 200

@app.route("/define", methods=["POST"])
def define():
    response = make_response(json.dumps({ "result": "true" }))
    response.set_cookie('ipv6', request.get_json()["ipv6"], httponly=True, samesite=None, max_age=3600)
    return response

@app.route("/ip")
def ip():
    return request.cookies.get("ipv6"), 200

async def loop():
    while True:
        await asyncio.sleep(10)
        try:
            if os.getenv("DEBUG") == "false":
                requests.get("https://verifai-service.onrender.com")
        except Exception as e:
            print(e)
            pass

def run_flask():
        app.run("0.0.0.0", port=12345)

async def main():
    try:
        flask_thread = Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        loop_task = asyncio.create_task(loop())
        await loop_task
    except asyncio.CancelledError:
        os._exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        queue.close()