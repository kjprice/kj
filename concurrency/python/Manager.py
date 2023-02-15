from typing import Dict, List, Optional, Type
from bs4 import BeautifulSoup as BS
import warnings
import requests
import multiprocessing
from multiprocessing import Manager as ProcessManager
from multiprocessing.managers import ListProxy, DictProxy
from python.listeners.db_listener import DBListener
from python.listeners.listener import Listener
from python.listeners.listener_message_hub import ListenerMessageHub
from python.workers import SingleInputWorker, Worker

warnings.simplefilter("ignore", UserWarning)
# warnings.simplefilter('ignore', InsecureRequestWarning)

class Manager():
  def __init__(
    self,
    namespace: str,
    inputs: List,
    WorkerClass: Type[Worker],
    num_workers: int,
    ListenerClass: Optional[Type[Listener]] = None,
    listener_class_kw_args = {},
    message_list_to_listener: Optional[ListProxy] = None,
    message_list_to_worker: Optional[ListProxy] = None,
    message_mongo_queue_finished: Optional[DictProxy] = None,
    continuous_workers: List[Type[SingleInputWorker]] = [],
    mongo_workers_to_create: int = 1,
    worker_kw_args: Dict = {}
  ) -> None:
    self.namespace = namespace
    jobs = []
    continuous_jobs = []
    job_queue = multiprocessing.Queue()
    # https://docs.python.org/3/library/multiprocessing.html#proxy-objects
    self.manager = ProcessManager()
    if message_list_to_listener is None:
      message_list_to_listener = self.manager.list()
    if message_list_to_worker is None:
      message_list_to_worker = self.manager.list()
    if message_mongo_queue_finished is None:
      message_mongo_queue_finished = self.manager.dict()
      # message_mongo_queue_finished['mongo_queue_finished'] = {}
    
    # TODO: Should this be an optional param?
    mongo_update_queue = self.manager.list()

    config_dict = self.manager.dict()

    message_lists_from_workers = []

    for continuous_worker in continuous_workers:
      message_list_from_worker = self.manager.list()
      message_lists_from_workers.append(message_list_from_worker)
      p = continuous_worker(message_list_to_listener=message_list_to_listener, message_list_from_worker=message_list_from_worker, config_dict=config_dict, message_list_to_worker=message_list_to_worker, mongo_update_queue=mongo_update_queue, message_mongo_queue_finished=message_mongo_queue_finished)
      continuous_jobs.append(p)
      p.start()

    for i in range(num_workers):
      message_list_from_worker = self.manager.list()
      message_lists_from_workers.append(message_list_from_worker)
      p = WorkerClass(
        job_queue=job_queue,
        config_dict=config_dict,
        message_list_from_worker=message_list_from_worker,
        message_list_to_listener=message_list_to_listener,
        message_list_to_worker=message_list_to_worker,
        mongo_update_queue=mongo_update_queue,
        message_mongo_queue_finished=message_mongo_queue_finished,
        worker_number=i,
        **worker_kw_args,
      )
      jobs.append(p)
      p.start()
    for input in inputs:
      job_queue.put(input)
    if ListenerClass is not None:
      message_hub = ListenerMessageHub(
        config_dict=config_dict,
        message_list_to_listener=message_list_to_listener,
        message_lists_from_workers=message_lists_from_workers)
      jobs.append(message_hub)
      message_hub.start()
      
      listener = ListenerClass(
        namespace=self.namespace,
        config_dict=config_dict,
        message_list_to_listener=message_list_to_listener,
        message_list_to_worker=message_list_to_worker,
        num_workers=num_workers,
        input_total_count=len(inputs),
        **listener_class_kw_args
      )
      jobs.append(listener)
      listener.start()
    
    for i in range(mongo_workers_to_create):
      db_listener = DBListener(
        listener_number=i,
        config_dict=config_dict,
        message_list_to_listener=message_list_to_listener,
        message_list_to_worker=message_list_to_worker,
        mongo_update_queue=mongo_update_queue,
        message_mongo_queue_finished=message_mongo_queue_finished,
        num_workers=num_workers,
      )
      jobs.append(db_listener)
      db_listener.start()

    # Send None for each worker to check and quit.
    for j in jobs:
      job_queue.put(None)
    all_jobs = continuous_jobs + jobs
    for j in all_jobs:
      j.join()

if __name__ == '__main__':
  class ExampleWorker(Worker):
    def __init__(self, job_queue):
      super().__init__(job_queue)
    def handle_input(self, input):
      url = input.strip() # input is a url
      try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
        response = requests.get(url, headers=headers, verify=False, allow_redirects=False, stream=True,
                                      timeout=10)
        soup = BS(response.text)
        return url + ' - Title: ', soup.title
      except requests.RequestException as e:
        print(url + ' - TimeOut!')
    def handle_output(self, output):
      print(output)
      pass
    
  urls = ['https://google.com'] * 10
  manager = Manager('example_manager', urls, ExampleWorker, 5)
