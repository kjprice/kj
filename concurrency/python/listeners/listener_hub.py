from typing import List
import time
import multiprocessing
from multiprocessing.managers import ListProxy, DictProxy

class ListenerMessageHub(multiprocessing.Process):
  def __init__(
    self,
    config_dict: DictProxy,
    message_list_to_listener: ListProxy,
    message_lists_from_workers: List[ListProxy]
  ) -> None:
    super().__init__()
    self.config_dict = config_dict
    self.message_list_to_listener = message_list_to_listener
    self.message_lists_from_workers = message_lists_from_workers

  def handle_messages(self):
    new_messages = []
    for message_list in self.message_lists_from_workers:
      if len(message_list) > 0:
        messages = message_list[:]
        del message_list[:len(messages)]
        for message in messages:
          new_messages.append(message)
    
    if len(new_messages) > 0:
      self.message_list_to_listener.extend(new_messages)
    time.sleep(0.000001)


  def run(self):
    while True:
      if 'WORKERS_FINISHED' in self.config_dict:
        return

      self.handle_messages()
  