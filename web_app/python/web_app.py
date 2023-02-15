# TODO:
# Call this like we do  for run_concurrently- Manager
# TODO: Move to config
BROWSERS_ROOM_NAME = 'browsers'

import os
import time
from typing import Dict, List, Optional
from python.misc import get_local_ip

import eventlet
import socketio

SOCKET_IO_SERVER_PORT = 9191


class WebApp():
  def __init__(self, static_files_map: Optional[Dict[str, str]] = None) -> None:
    self.jobs_running_by_fn_name = {}
    self.raspi_info_by_hostname = {}
    self.static_files_map = static_files_map
    # self.static_files_map = {
    #     '/': os.path.join(STATIC_DIR, 'index.html'),
    #     '/static': os.path.join(STATIC_DIR, 'static')
    # }

    self.start_socket_server()

  def start_socket_server(self):
    sio = socketio.Server(cors_allowed_origins='*')
    # TODO: Set static files
    app = socketio.WSGIApp(sio, static_files=self.static_files_map)

    # From all clients
    @sio.event
    def connect(sid, environ):
      print('connect ', sid)
    
    @sio.event
    def perform_text_search(sid, text):
      print('yay', text)

    @sio.event
    def disconnect(sid):
        print('disconnect ', sid)

    # From all backend clients (not browser)
    @sio.event
    def send_output(sid, data):
      sio.emit('send_output', data, room=BROWSERS_ROOM_NAME)

    eventlet.wsgi.server(eventlet.listen((get_local_ip(), SOCKET_IO_SERVER_PORT)), app)

if __name__ == '__main__':
  WebApp()
  