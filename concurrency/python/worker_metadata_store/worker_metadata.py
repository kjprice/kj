import time
from typing import Dict, Optional, Tuple

import numpy as np

def calculate_time_passed(time_start, decimal_point=6):
  time_end = time.time()

  return float(np.round(time_end - time_start, decimal_point))

class StepStats:
  def __init__(self, description: str) -> None:
    self.description = description
    self.status = "running"
    self.time_start = 0.0
    self.total_time_running = 0.0
    self.number_times_ran = 0
    self.average_run_time = 0
    self.last_time_passed = -1.0
  
  def on_start(self):
    self.time_start = time.time()
    self.status = "running"
  
  def on_end(self) -> float:
    if self.time_start == 0:
      raise Exception('Step never started')

    self.last_time_passed = calculate_time_passed(self.time_start)
    self.total_time_running += self.last_time_passed
    self.number_times_ran += 1
    self.average_run_time = self.total_time_running / self.number_times_ran
    self.time_start = 0.0
    return self.last_time_passed

class StepStatsManager:
  def __init__(self) -> None:
    self.current_step_number = 0
    self.current_description = ""
    self.step_stats_by_description = {}
  
  def get_step_by_description(self, description: str) -> StepStats:
    if not description in self.step_stats_by_description:
      self.step_stats_by_description[description] = StepStats(description)
    
    return self.step_stats_by_description[description]
  
  def change_step(self, step_number: int, description: str) -> Tuple[Optional[float], Optional[float]]:
    current_step = self.current_step
    average_run_time = None
    last_time_passed = None
    if current_step is not None:
      last_time_passed = current_step.on_end()
      average_run_time = current_step.average_run_time
    
    self.current_step_number = step_number
    self.current_description = description
    self.get_step_by_description(self.current_description).on_start()

    return average_run_time, last_time_passed
  
  @property
  def current_step(self) -> Optional[StepStats]:
    if self.current_description == '':
      return None
    
    return self.get_step_by_description(self.current_description)
  
class WorkerMetadata:
  def __init__(self, worker_number: int) -> None:
    self.step_stats_manager = StepStatsManager()
    self.worker_number = worker_number
    self.time_initialized = time.time()
    self.time_input_start = 0
    self.last_input_process_time = 0
    self.total_process_time = 0
    self.inputs_started = 0
    self.inputs_completed = 0
    self.error = False
    self.inputs_completed = 0
    self.average_time_per_job = -1
  
  def update(self, **kwargs):
    fields_dict = self.__dict__
    for key in kwargs.keys():
      if key != 'worker_number' and key in fields_dict:
        fields_dict[key] = kwargs[key]
      else:
        raise ValueError(f'Unknown kwargs key "{key}"')
  
  def on_complete(self):
    time_passed = calculate_time_passed(self.time_initialized)
    self.update(total_process_time=time_passed)

  def on_input_start(self):
    inputs_started = self.inputs_started + 1
    self.update(inputs_started=inputs_started, time_input_start=time.time())

  def on_input_end(self) -> Optional[float]:
    inputs_completed = self.inputs_completed + 1
    if self.time_input_start is None:
      return None
    time_passed = calculate_time_passed(self.time_input_start)
    average_time_per_job = time_passed / inputs_completed

    self.update(
      inputs_completed=inputs_completed,
      time_input_start=None,
      last_input_process_time=time_passed,
      average_time_per_job=average_time_per_job
    )

    return time_passed
  
  def on_step_change(self, step_number: int, step_description: str) -> Tuple[Optional[float], Optional[float]]:
    # TODO: This
    return self.step_stats_manager.change_step(step_number, step_description)
  
  def to_dict(self) -> Dict:
    fields_dict = self.__dict__.copy()

    fields_dict['step_number'] = self.step_stats_manager.current_step_number
    fields_dict['step_description'] = self.step_stats_manager.current_description

    fields_to_ignore_on_save = [
      'time_initialized',
      'time_input_start',
      'step_stats_manager'
    ]
    for field_name in fields_to_ignore_on_save:
      del fields_dict[field_name]
    
    return fields_dict
