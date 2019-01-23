# encoding=utf-8

import threading, hashlib, socket, base64

'''
    一  WebSocket 是一种标准协议
        一种标准协议,用于在客户端和服务端之间进行双向数据传输
        基于TCP 的一种独立实现

    二  通信过程：
        客户端请求报文 Header
        创建 WebSocket 对象
        服务端响应报文 Header
            创建主线程，用于实现接受 WebSocket 建立请求
        进行通信
            a. 服务端解析 WebSocket 报文
            b. 服务端发送 WebSocket 报文

    三  应用：
        多个用户之间进行交互
        需要频繁地向服务端请求更新数据
            比如弹幕、消息订阅、多玩家游戏、协同编辑、
            股票基金实时报价、视频会议、在线教育等
            需要高实时的场景

    案例聊天室：
        客户端
        服务端

        测试页面 view code
'''

# 客户端
global clients
clients = {}

# 通知客户端
def notify(message):
    for conn in clients.values():
        conn.send('%c%c%s' % (0x81, len(message), message))

class websocket_thread(threading.Thread):
    def __init__(self, conn, username):
        super(websocket_thread, self).__init__()
        self.conn = conn
        self.username = username

    def run(self):
        print('New websocket client joined')
        data = self.conn.recv(1024)
        hreaders = self.parse_headers(data)
        token = self.genrate_token(hreaders['Sec_-WebSocket-Key'])
        self.conn.send(
            '\
                HTTP/1.1 101 WebSocket Protocol Hybi-10\r\n\
                Upgrade: WebSocket\r\n\
                Connection: Upgrade\r\n\
                Sec-WebSocket-Accept: %s\r\n\r\n' % token
        )
        while True:
            try:
                data = self.conn.recv(1024)
            except socket.error as e:
                print("unexpected error: ", e)
                clients.pop(self.username)
                break

            data = self.parse_data(data)
            if len(data) == 0:
                continue
            message = self.username + ":" + data 
            notify(message)

    def parse_data(self, msg):
        v = ord(msg[1]) & 0x7f
        if v == 0x7e:
            p = 4
        elif v == 0x7f:
            p = 10
        else:
            p = 2
        mask = msg[p:p+4]
        data = msg[p+4:]
        return ''.join([chr(ord(v) ^ ord(mask[k%4]))\
                for k, v in enumerate(data)])

    def parse_headers(self, msg):
        headers = {}
        header, data = msg.split('\r\n\r\n', 1)
        for line in header.split('\r\n')[1:]:
            key, value = line.split(':', 1)
            headers[key] = value 
        headers['data'] = data
        return headers

    def genrate_token(self, msg):
        key = msg + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        ser_key = hashlib.sha1(key).digest()
        return base64.b64encode(ser_key)



# 服务端
class websocket_server(threading.Thread):
    def __init__(self, port):
        super(websocket_server, self).__init__()
        self.port = port

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind('127.0.0.1', self.port)
        sock.listen(5)
        print('websocket server started')

        while True:
            conn, address = sock.accept()
            try:
                username = "ID" + str(address[1])
                thread = websocket_thread(conn, username)
                thread.start()
                clients[username] = conn
            except socket.timeout:
                print('websocket conn timeout')


if __name__ == "__main__":
    server = websocket_server(8888)
    server.start()