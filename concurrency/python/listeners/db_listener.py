from typing import Any
import time
import multiprocessing
from multiprocessing.managers import ListProxy, DictProxy
from python.concurrent.worker_messages.mongo_update import MongoUpdate
from python.misc.db import connect_db

class DBListener(multiprocessing.Process):
  def __init__(
    self,
    listener_number: int,
    config_dict: DictProxy,
    message_list_to_listener: ListProxy,
    message_list_to_worker: ListProxy,
    mongo_update_queue: ListProxy,
    message_mongo_queue_finished: DictProxy,
    num_workers: int,
  ) -> None:
    super().__init__()
    self.listener_number = listener_number
    self.config_dict = config_dict
    self.message_list_to_listener = message_list_to_listener
    self.message_list_to_worker = message_list_to_worker
    self.mongo_update_queue = mongo_update_queue
    self.message_mongo_queue_finished = message_mongo_queue_finished
    self.num_workers = num_workers
    self._db = None

  def connect_to_db(self):
    time_to_wait = self.num_workers / 10
    # print(f'Waiting {time_to_wait} seconds for other processes to warm up.')
    time.sleep(time_to_wait)
    self._db = connect_db()

    return self._db

  @property
  def db(self):
    if self._db is None:
      return self.connect_to_db()

    return self._db

  # TODO: Do we need this?
  def send_message(self, message: Any) -> None:
    self.message_list_to_worker.append(message)
  
  def send_mongo_finished(self, finish_confirmation_key: str) -> None:
    self.message_mongo_queue_finished[finish_confirmation_key] = True

  def update_mongo(self, message: MongoUpdate):
    update_args = {
      'filter': message.query,
      'update': message.update,
      'upsert': message.upsert
    }

    db_connection = self.db[message.collection_name]

    if message.update_many:
      db_connection.update_many(**update_args)
    else:
      db_connection.update_one(**update_args)
    
    finish_confirmation_key = message.finish_confirmation_key
    if finish_confirmation_key is not None:
      self.send_mongo_finished(finish_confirmation_key)
  
  def write_messages_count(self):
    filepath = f'db_listener_messages_{self.listener_number}.txt'
    with open(filepath, 'w') as f:
      f.write(str(len(self.mongo_update_queue)))

  def run(self):
    i = 0
    while True:
      if 'ABORT_IMMEDIATELY' in self.config_dict:
        return
      if len(self.mongo_update_queue) > 0:
        i += 1
        if i % 10 == 0:
          self.write_messages_count()
        
        # The queue may already be empty at this point
        try:
          mongo_message = self.mongo_update_queue.pop(0)
          self.update_mongo(mongo_message)
        except IndexError:
          # TODO: Log how many errors
          pass
      # Only exit here once queue is empty
      elif 'WORKERS_FINISHED' in self.config_dict:
        self.write_messages_count()
        return

      
      time.sleep(0.0001)
