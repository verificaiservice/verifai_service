import pymysql
import requests
import os
from dotenv import load_dotenv
import asyncio
import time
import instaloader

load_dotenv()

temp_path = "public/images"

L = instaloader.Instaloader(
    filename_pattern="vl_{shortcode}",
    dirname_pattern=temp_path,
    download_videos=True,
    download_video_thumbnails=True,
    download_geotags=False,
    save_metadata=False,
    download_comments=False,
    post_metadata_txt_pattern=''
)

username = os.getenv("IG_USERNAME")
password = ""
if os.path.isfile(f"{os.getcwd()}/session/{username}"):
    L.load_session_from_file(username, filename=f"{os.getcwd()}/session/{username}")  # se já tiver salvo antes
else:
    L.login(username, password)  # Vai fazer o login e manter a sessão
    L.save_session_to_file(filename=f"{os.getcwd()}/session/{username}")

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

queue.add_modify_query("""
CREATE TABLE IF NOT EXISTS parcial_links (
    parcial_id INT AUTO_INCREMENT PRIMARY KEY,
    id INT,
    link VARCHAR(100)
)
""")

# queue.add_modify_query("""ALTER TABLE parcial_links ADD caption VARCHAR(1000)""")

# queue.add_get_query("DELETE FROM parcial_links")

lines = queue.add_get_query("SELECT * FROM links WHERE id NOT IN (SELECT id FROM parcial_links)")

# queue.add_modify_query("""UPDATE parcial_links SET link = CONCAT('https://6v9s4f5f-12345.brs.devtunnels.ms/images/vl_',
#     SUBSTRING_INDEX(SUBSTRING_INDEX(link, 'vl_', -1), '.', 1),
#     '.',
#     SUBSTRING_INDEX(link, '.', -1)
# );""")

# lines = queue.add_get_query("SELECT * FROM parcial_links")

# lines = []

def get_shortcode_from_url(url):
    url = url.split("?")[0]
    return url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]

for line in lines:
    # shortcode = line["link"].split("v_")[1].split(".")[0]
    # extension = line["link"].split(".")[1]
    # queue.add_modify_query("UPDATE parcial_links SET link=%s", (line["id"], f"localhost:12345/public/images/vl_{str(shortcode)}.{extension}"))
    
    link = line["link"]
    if link.startswith("https://www.instagram.com/p/") or link.startswith("https://www.instagram.com/reel/"):
        shortcode = get_shortcode_from_url(link)
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        caption = post.caption if post.caption else ""
        extension = "mp4" if post.is_video else "jpg"
        L.download_post(post, target=temp_path)

        queue.add_modify_query("INSERT INTO parcial_links (id,link, caption) VALUES(%s, %s, %s)", (line["id"], f"localhost:12345/public/images/v_{str(shortcode)}.{extension}?shortcode={str(shortcode)}", caption))

    # Se for uma postagem compartilhada em forma de link
    elif link.startswith("https://www.instagram.com/share/"):
        response = requests.get(link, allow_redirects=True)
        url = response.url
        shortcode = get_shortcode_from_url(url)
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        caption = post.caption if post.caption else ""
        extension = "mp4" if post.is_video else "jpg"
        L.download_post(post, target=temp_path)

        queue.add_modify_query("INSERT INTO parcial_links (id,link, caption) VALUES(%s, %s, %s)", (line["id"], f"localhost:12345/public/images/v_{str(shortcode)}.{extension}?shortcode={str(shortcode)}", caption))