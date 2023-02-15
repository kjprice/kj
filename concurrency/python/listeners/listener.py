from typing import Any, Dict, Optional, Type
import time
import multiprocessing
from multiprocessing.managers import ListProxy, DictProxy

import numpy as np
import pandas as pd

from python.worker_messages.worker_stats import StepChangeStats, WorkerFinishedStats, WorkerMetadataInputEndStats, WorkerMetadataInputErrorStats, WorkerMetadataInputStartStats, WorkerStats
from python.worker_metadata_store.worker_metadata import WorkerMetadata
from python.worker_metadata_store.worker_metadata_manager import WorkersMetadataManager
from misc.python.format_time import format_time

class Listener(multiprocessing.Process):
  def __init__(
    self,
    config_dict: DictProxy,
    namespace: str,
    message_list_to_listener: ListProxy,
    message_list_to_worker: ListProxy,
    num_workers: int,
    input_total_count: int,
    WorkerMetadataClass: Optional[Type[WorkerMetadata]] = None
  ) -> None:
    super().__init__()
    self.config_dict = config_dict
    self.workers_metadata_manager = WorkersMetadataManager(worker_directory=namespace, WorkerMetadataClass=WorkerMetadataClass)
    self.message_list_to_listener = message_list_to_listener
    self.message_list_to_worker = message_list_to_worker
    self.num_workers = num_workers
    self.finished_count = 0
    self._db = None
    self.average_time_completion_for_input = -1
    self.input_total_count = input_total_count
    self.input_completed_count = 0
    self.last_print_message = 0.0
    self.SECONDS_BETWEEN_PRINT = 0.1

  def get_and_remove_message(self):
    all_messages_count = 0
    while True:
      while len(self.message_list_to_listener) > 0:
        new_messages = self.message_list_to_listener[:]
        del self.message_list_to_listener[:len(new_messages)]
        for new_messages_count, message in enumerate(new_messages):
          all_messages_count += 1
          if all_messages_count % 10 == 0:
            # TODO: Move this logging to get_default_stats_to_print
            with open('listener_messages.txt', 'w') as f:
              stats = [
                f'messages in listener: {len(self.message_list_to_listener)}',
                f'all messages handled: {all_messages_count}',
                f'Currently handling: {new_messages_count} of {len(new_messages)}',
              ]
              f.write('\n'.join(stats))
          yield message
      time.sleep(0.000001)
  def handle_stats(self, stats: WorkerStats):
    # print(stats.stats)
    pass

  def send_message(self, message: Any) -> None:
    self.message_list_to_worker.append(message)
  
  # TODO: This is unused - call when user requests abort
  def send_abort_message(self):
    self.config_dict['ABORT_IMMEDIATELY'] = True

  def send_workers_finished_message(self):
    self.config_dict['WORKERS_FINISHED'] = True

  def handle_worker_finished(self, message: WorkerFinishedStats):
    if self.workers_metadata_manager is not None:
      self.workers_metadata_manager.handle_worker_finished(message.worker_number)
    self.finished_count += 1

  def handle_input_start(self, message: WorkerMetadataInputStartStats):
    if self.workers_metadata_manager is not None:
      self.workers_metadata_manager.handle_input_start(message.worker_number)

  def handle_input_end(self, message: WorkerMetadataInputEndStats):
    self.input_completed_count += 1
    if self.workers_metadata_manager is not None:
      average_time = self.workers_metadata_manager.handle_input_end(message.worker_number)
      if average_time is None:
        return
      self.average_time_completion_for_input = float(np.round(average_time, 4))
      self.print_stats()

  def handle_input_error(self, message: WorkerMetadataInputErrorStats):
    if self.workers_metadata_manager is not None:
      self.workers_metadata_manager.handle_input_error(message.worker_number)

  def handle_step_change(self, stats: StepChangeStats):
    worker_number = stats.worker_number
    step_number = stats.step_number
    step_description = stats.step_description
    self.workers_metadata_manager.handle_step_change(worker_number, step_number=step_number, step_description=step_description)
  
  def save_all_metadata(self):
    self.workers_metadata_manager.save_all()

  def handle_messages(self):
    # TODO: If user hits escape key, then actually abort
    #           self.send_abort_message()

    for message in self.get_and_remove_message():
      if isinstance(message, WorkerFinishedStats):
        self.handle_worker_finished(message)
        if self.finished_count == self.num_workers:
          self.save_all_metadata()
          self.print_stats(force=True)
          self.send_workers_finished_message()
          return
      # TODO: Consider consolidating the way that we write logs to the filesystem with a new worker(s)
      elif isinstance(message, WorkerMetadataInputStartStats):
        self.handle_input_start(message)
      elif isinstance(message, WorkerMetadataInputEndStats):
        self.handle_input_end(message)
      elif isinstance(message, WorkerMetadataInputErrorStats):
        self.handle_input_error(message)
      elif isinstance(message, StepChangeStats):
        self.handle_step_change(message)
      elif isinstance(message, WorkerStats):
        self.handle_stats(message)
      else:
        raise TypeError(f'Cannot handle message of type "{type(message)}"')
  def get_default_stats_to_print(self) -> Dict:
    # TODO: Add active number of messages here
      active_workers_count = self.active_workers_count
      avg_completion_time = self.average_time_completion_for_input
      estimate_time_to_completion = self.estimate_time_to_completion

      return {
        'active/total workers': f'{active_workers_count}/{self.num_workers}',
        'avg. duration': f'{format_time(avg_completion_time)}',
        'ETC': f'{format_time(estimate_time_to_completion)}',
      }
  
  def print_stats(self, force=False):
    pass

  def can_print_stats(self, force=False):
    if force:
      return True
    now = time.time()
    if now > (self.last_print_message + self.SECONDS_BETWEEN_PRINT):
      self.last_print_message = now
      return True

  def print_stats_throttle(self, stats: Dict, force=False):
    if not self.can_print_stats(force):
      return
    df = pd.DataFrame([stats])

    LINE_UP = '\033[1A' # Can move up any number of times
    LINE_CLEAR = '\x1b[2K'

    column_renaming = {}
    for c in df.columns:
      column_renaming[c] = f'{c} |'
    df.rename(columns=column_renaming, inplace=True)

    df_string = df.to_string(index=False, justify='left')

    print(LINE_UP, end=LINE_CLEAR)
    print(LINE_UP, end=LINE_CLEAR)
    print(LINE_UP, end=LINE_CLEAR)
    print()

    print(df_string)

  def run(self):
    self.handle_messages()

  @property
  def active_workers_count(self):
    return self.num_workers - self.finished_count

  @property
  def remaining_inputs_count(self):
    return self.input_total_count - self.input_completed_count

  @property
  def estimate_time_to_completion(self) -> float:
    return self.remaining_inputs_count * self.average_time_completion_for_input / self.num_workers
