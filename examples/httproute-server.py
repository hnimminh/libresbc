#!/usr/bin/env python3
"""
Very simple HTTP server in python for logging requests
Usage: httproute-server.py [<ipaddr> <port>]
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import socket


DATA = ['AWS', 'AZURE']

class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        logging.info(f"GET request,\nPath: {str(self.path)}\nHeaders:\n{str(self.headers)}\n")
        self._set_response()
        self.wfile.write(json.dumps(DATA).encode('utf-8'))
        self

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        logging.info(f"POST request,\nPath: {str(self.path)}\nHeaders:\n{str(self.headers)}\nBody:\n{post_data.decode('utf-8')}\n")
        self._set_response()
        self.wfile.write(json.dumps({'success': True}).encode('utf-8'))


def run(server_class=HTTPServer, handler_class=S, ipaddr='127.0.0.1', port=54321):
    logging.basicConfig(level=logging.INFO)
    if ':' in ipaddr:
        server_class.address_family = socket.AF_INET6
    server_address = (ipaddr, port)
    httpd = server_class(server_address, handler_class)
    logging.info(f'Starting httpd, listen on {ipaddr}:{port}\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')

if __name__ == '__main__':
    from sys import argv

    if len(argv) == 3:
        run(ipaddr=str(argv[1]), port=int(argv[2]))
    else:
        run()
