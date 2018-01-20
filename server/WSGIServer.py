import socket
import sys
import io


class WSGIServer:

    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 1

    def __init__(self, host, port):
        self.listen_sock = socket.socket(self.address_family, self.socket_type)
        self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_sock.bind((host, port))
        self.listen_sock.listen(self.request_queue_size)

        self.server_name = socket.getfqdn(host)
        self.server_host = host
        self.server_port = port

        self.client_connection = None
        self.client_address = None
        self.request_method = None
        self.request_data = None
        self.request_version = None
        self.path = None
        self.headers_set = []
        self.application = None

    def set_app(self, app):
        self.application = app

    def server_forever(self):
        while True:
            self.client_connection, self.client_address = self.listen_sock.accept()
            self.handle_one_request()

    def handle_one_request(self):
        self.request_data = self.client_connection.recv(1024)

        print(self.request_data)

        self.parse_request(str(self.request_data, encoding='utf-8'))
        env = self.get_environ()
        result = self.application(env, self.start_response)
        self.finish_response(result)

    def parse_request(self, text):
        if len(text.splitlines()) > 0:
            request_line = text.splitlines()[0]
            request_line = request_line.rstrip('\r\n')

            self.request_method, self.path, self.request_version = request_line.split()

    def get_environ(self):
        env = {
            # WSGI variables
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.input': io.BytesIO(self.request_data),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,

            # CGI variables
            'REQUEST_METHOD': self.request_method,
            'PATH_INFO': self.path,
            'SERVER_NAME': self.server_host,
            'SERVER_PORT': str(self.server_port),
        }

        return env

    def start_response(self, status, response_headers, exc_info=None):
        server_headers = [
            ('Date', '2018-1-21'),
            ('Server', 'WSGIServer 0.2'),
        ]
        self.headers_set = [status, response_headers + server_headers]

    def finish_response(self, result):
        try:
            status, response_headers = self.headers_set
            response = 'HTTP/1.1 {status}\r\n'.format(status=status)
            for header in response_headers:
                response += '{0}: {1}\r\n'.format(*header)
            response += '\r\n'
            response = response.encode('utf-8')
            for data in result:
                response += data

            print(response)

            self.client_connection.sendall(response)
        finally:
            self.client_connection.close()


HOST, PORT = '0.0.0.0', 3456


def make_server(host, port, app):
    server = WSGIServer(host, port)
    server.set_app(app)

    return server


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('Provide a WSGI application object as module:callable')

    app_path = sys.argv[1]
    module, application = app_path.split(':')

    module = __import__(module)
    application = getattr(module, application)
    httpd = make_server(HOST, PORT, application)
    print('WSGIServer: Serving HTTP on port {port} ...'.format(port=PORT))
    httpd.server_forever()
