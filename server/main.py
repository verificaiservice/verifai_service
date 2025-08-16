from quart import Quart, request, send_file, make_response
import json
import pymysql
import requests
import os
from dotenv import load_dotenv
import asyncio
import time
import traceback
import httpx
import uvicorn
from socketio import AsyncClient as AsyncClientSocketIO

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
        autocommit=True
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
            for id in list(self.queue.keys()):
                current_queue = self.queue[id]

                if current_queue[1] == "get":
                    start = time.time()
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
    
    async def add_get_query(self, *string: str):
        return await self.process_query(string, type="get")

    async def add_modify_query(self, *string: str):
        return await self.process_query(string, type="modify")
    

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
app = Quart(__name__)

io: AsyncClientSocketIO | None = None

# app = Flask(__name__)
# CORS(app, supports_credentials=True)

@app.route("/", methods=["GET"])
async def home():
    return await send_file("public/index.html")

@app.route("/assets/<path:filename>", methods=["GET"])
async def assets(filename):
    return await send_file("public/assets/" + filename)

@app.route("/images/<path:filename>", methods=["GET"])
async def images(filename):
    return await send_file("public/images/" + filename)

# rows = await queue.add_modify_query("""SET @pos := 0;
# UPDATE links
# JOIN (
#     SELECT id, @pos := @pos + 1 AS nova_ordem
#     FROM links
#     ORDER BY id
# ) AS ordenado
# ON links.id = ordenado.id
# SET links.id = ordenado.nova_ordem""")

# await queue.add_modify_query("DROP TABLE links_temp2;")
# rows = queue.add_get_query("SELECT * FROM ( SELECT *, (SELECT COUNT(*) AS n_repeticoes FROM links AS lp WHERE lp.link = la.link) AS n_repeticoes FROM links AS la ) AS sub WHERE n_repeticoes > 1")
# print(rows)
# rows = await queue.add_modify_query("""DELETE l1
# FROM links l1
# JOIN (
#     SELECT link, MAX(id) AS max_id
#     FROM links
#     GROUP BY link
#     HAVING COUNT(*) > 1
# ) AS sub ON l1.link = sub.link AND l1.id = sub.max_id;""")
# await queue.add_modify_query("""UPDATE links
# SET link = CASE 
#              WHEN RIGHT(SUBSTRING_INDEX(link, '?', 1), 1) = '/' THEN 
#                LEFT(SUBSTRING_INDEX(link, '?', 1), LENGTH(SUBSTRING_INDEX(link, '?', 1)) - 1)
#              ELSE 
#                SUBSTRING_INDEX(link, '?', 1)
#           END
# WHERE link LIKE '%?%';""")
# await queue.add_modify_query("ALTER TABLE links MODIFY response VARCHAR(1500)")
# conn = get_connection()
# try:
#     with conn.cursor() as cursor:
#         cursor.execute("ALTER TABLE links MODIFY ipv6 VARCHAR(50);")
#         rows = conn.commit()
# finally:
#     conn.close()

@app.route("/list", methods=["POST"])
async def get_list():
    data = await request.get_json()
    page = data["page"]
    postsPerPage = data["postsPerPage"]
    init_post = page * postsPerPage

    rows = await queue.add_get_query(f"SELECT *, (SELECT COUNT(*) FROM links) AS n_posts, (SELECT COUNT(*) FROM links WHERE expect!=3 AND result!=2) AS n_posts_verified, (SELECT COUNT(*) FROM links WHERE expect=1) AS n_posts_true, (SELECT COUNT(*) FROM links WHERE expect=0) AS n_posts_false FROM links ORDER BY id LIMIT {init_post}, {postsPerPage}")
    return json.dumps({ "result": "true", "isAdmin": request.cookies.get("ipv6").startswith("2804:25ac:43c:fd00"), "data": rows }), 200


@app.route("/edit", methods=["GET","POST"])
async def edit():
    if request.method == "GET":
        return send_file("public/index.html")
    
    response = None

    try: 
        data = await request.get_json()

        type = data["type"]
        id = data["id"]

        if type == "get":
            row = (await queue.add_get_query("SELECT * FROM links WHERE id=%s", (id,)))[0]
            response = json.dumps({ "result": "true", "data": row }), 200

        else:
            tipo = int(data["type"])
            expect = int(data["expect"])
            ipv6 = request.cookies.get("ipv6")
            await queue.add_modify_query("UPDATE links SET type=%s, expect=%s, ipv6=%s WHERE id=%s", (tipo, expect, ipv6, id))
            response = json.dumps({ "result": "true" }), 200
        
        return response
    
    except Exception as e:
        print(e)
        return json.dumps({ "result": "false" }), 200

@app.route("/insert", methods=["GET", "POST"])
async def insert():
    if request.method == "GET":
        return send_file("public/index.html")
    
    try:
        data = await request.get_json()
        link = data["link"]
        if len(await queue.add_get_query("SELECT id FROM links WHERE link=%s",(link))) > 0:
            return json.dumps({ "result": "false", "message": "exists" })

        tipo = int(data["type"])
        expect = int(data["expect"])
        ipv6 = request.cookies.get("ipv6")
        timestamp = int(time.time())
        await queue.add_modify_query("INSERT INTO links (link, type, expect, result, response, ipv6, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)", (link, tipo, expect, 2, "", ipv6, timestamp))
        return json.dumps({ "result": "true" }), 200
    except Exception as e:
        print(e)
        return json.dumps({ "result": "false" }), 200

@app.route("/delete", methods=["POST"])
async def delete():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            data = await request.get_json()
            id = int(data["id"])
            cursor.execute("DELETE FROM links WHERE id = %s", (id,))
            conn.commit()
    except Exception as e:
        print(e)
    finally:
        conn.close()
        # return get_list()
        return await get_list()

@app.route("/verify", methods=["POST"])
async def verify():
    try:
        data = await request.get_json()
        id_start = data["id_start"]
        id_end = data["id_end"]
        rows = await queue.add_get_query("SELECT *, (SELECT link FROM parcial_links WHERE id = l.id) AS image_link, (SELECT caption FROM parcial_links WHERE id = l.id) AS caption FROM links l WHERE id >= %s AND id <= %s", (id_start, id_end))



        responses = {}

        io = AsyncClientSocketIO()
        await io.connect("http://localhost:5000" if os.getenv("DEBUG") == "true" else "https://verifai-w7pk.onrender.com")

        for row in rows:
            data = {
                "VERIFY_TOKEN": os.getenv("VERIFY_TOKEN"),
            }
            # if "image_link" in row:
            if "impossible_key" in row:
                image_link = row["image_link"]
                title = row["caption"]

                is_video = ".mp4" in image_link
                shortcode = image_link.split("vl_")[1].split("?")[0].split(".")[0]
                data["message"] = {
                    'attachments': [
                        {
                            'type': 'ig_reel' if is_video else 'share',
                            'payload': {
                                'reel_video_id': shortcode,
                                'title': title,
                                'url': image_link
                            }
                        }
                    ]
                }
                data["link"] = ""
            else:
                data["link"] = row["link"]

            event = asyncio.Event()
           
            async def get_response(response):
                if len(response)  > 300:
                    verify_result = 1 if "fato" in response[:12] else 0
                    responses[str(row["id"])] = { "result": verify_result, "response": response }

                    await queue.add_modify_query("UPDATE links SET result = %s, response = %s WHERE id = %s", (verify_result, response, int(row["id"])))
                    event.set()

                elif response == "Link inválido. Verifique-o e tente novamente.":
                    event.set()

            await io.emit("verify",json.dumps(data))

            # Register the listener
            io.on("updated_message", get_response)

            # Wait get_response execution
            await event.wait()

        return await get_list()
    
    except Exception as e:
        traceback.print_exc()
        return json.dumps({ "result": "false" }), 200

@app.route("/has_defined")
def has_defined():
    return json.dumps({ "setted": True if request.cookies.get("ipv6") else False }), 200

@app.route("/define", methods=["POST"])
async def define():
    response = await make_response(json.dumps({ "result": "true" }))
    response.set_cookie('ipv6', (await request.get_json())["ipv6"], httponly=True, samesite=None, max_age=3600)
    return response

@app.route("/ip")
def ip():
    return request.cookies.get("ipv6"), 200

@app.after_request
async def dynamic_cors(response):
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Length, Content-Type"
    return response

# async def create_io_client():
    # global io

    #     await io.wait()

async def keep_alive_loop():
    while True:
        await asyncio.sleep(10)
        try:
            async with httpx.AsyncClient() as client:
                await client.get("https://verifai-service.onrender.com")
        except:
            pass

# Inicializa tudo no modo assíncrono
async def main():
    # Cria a tarefa do loop de keep-alive
    loop_task = asyncio.create_task(keep_alive_loop())
    # asyncio.create_task(create_io_client())

    # Configura e inicia o servidor Uvicorn
    config = uvicorn.Config(app=app, host="0.0.0.0", port=12345)
    server = uvicorn.Server(config)
    await server.serve()

    # (opcional) espera o loop de keep-alive (só após shutdown)
    await loop_task

# Entry point
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        os._exit(0)