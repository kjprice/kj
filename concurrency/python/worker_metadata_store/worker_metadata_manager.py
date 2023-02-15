import os
import time
from typing import Callable, Dict, List, Optional, Type

import numpy as np
import pandas as pd
from concurrency.python.worker_metadata_store.worker_metadata import WorkerMetadata

from misc.python.filesystem.ensure_directory_exists import ensure_directory_exists

#  WORKER_METADATA_DIRECTORY
def reorder_df_columns(df: pd.DataFrame, important_columns_order: List[str] = ['worker_number']) -> pd.DataFrame:
  all_columns = df.columns
  unimportant_columns = [column for column in all_columns if column not in important_columns_order]

  new_columns_order = important_columns_order + unimportant_columns

  return df[new_columns_order]

def create_workers_dataframe(workers_metadata: List[WorkerMetadata]) -> pd.DataFrame:
    metadata_dicts = [metadata.to_dict() for metadata in workers_metadata]
    df = pd.DataFrame(metadata_dicts)
    df = reorder_df_columns(df)

    return df

class StepRunTimes:
  def __init__(self, description: str, step_number: Optional[int] = -1) -> None:
    self.description = description
    self.total_time_running_average = 0.0
    self.number_times_ran = 0
    self.average_run_time = 0.0
    self.step_number = step_number
    self.last_run_time = -1.0
  def new_time(self, average_run_time_for_step: float, time_passed: float) -> float:
    self.total_time_running_average += average_run_time_for_step
    self.number_times_ran += 1
    self.average_run_time = self.total_time_running_average / self.number_times_ran
    self.last_run_time = time_passed

    return self.average_run_time
  
  @property
  def dict(self):
    return {
        'step_number': self.step_number,
        'description': self.description,
        'average': float(np.round(self.average_run_time, 6)),
        'last_run_time': self.last_run_time,
        'number_times_ran': self.number_times_ran
      }

class StepsRunTimesStore:
  def __init__(self) -> None:
    self.step_run_times_by_description = {}
  
  def get_step_run_times(self, description: str, step_number: Optional[int] = -1) -> StepRunTimes:
    if not description in self.step_run_times_by_description:
      self.step_run_times_by_description[description] = StepRunTimes(description, step_number)
    
    return self.step_run_times_by_description[description]
  def set_step_run_time(self, description: str, average_run_time_for_step: float, time_passed: float, step_number: int):
    step_run_times = self.get_step_run_times(description, step_number)
    step_run_times.new_time(average_run_time_for_step, time_passed)
  
  @staticmethod
  def to_dataframe(step_runs: List[Dict]) -> Optional[pd.DataFrame]:
    if len(step_runs) == 0:
      return None
    df = pd.DataFrame(step_runs)

    columns_order = ['step_number', 'average', 'last_run_time', 'number_times_ran', 'description']
    df = reorder_df_columns(df, important_columns_order=columns_order)

    return df.sort_values('step_number')
  
  def dict_from_description(self, description: str):
    return self.get_step_run_times(description).dict

  def dataframe_from_description(self, description: str):
    step_run_times = self.get_step_run_times(description)
    return StepsRunTimesStore.to_dataframe([step_run_times.dict])

  
  @property
  def all_serialized(self) -> List[Dict]:
    all_info = []
    for description in self.step_run_times_by_description.keys():
      step_run_time = self.get_step_run_times(description)
      all_info.append(step_run_time.dict)
    
    return all_info
  
  # TODO: Pass this
  @property
  def all_dataframe(self) -> Optional[pd.DataFrame]:
    return StepsRunTimesStore.to_dataframe(self.all_serialized)

class DataFrameAppendFile:
  def __init__(self) -> None:
    self.files_saved = set()
  
  def save_dataframe(self, df: pd.DataFrame, filepath: str):
    if not filepath in self.files_saved:
      df.to_csv(filepath, index=False)
      self.files_saved.add(filepath)
    else:
      df.to_csv(filepath, index=False, mode='a', header=False)

class DataFrameThrottleSave:
  def __init__(self, filepath: str, should_append=False, get_df:Optional[Callable] = None) -> None:
    self.filepath = filepath
    self.last_save = time.time()
    self.seconds_between_save = 2
    self.should_append = should_append
    self.records = []
    self.data_frame_append_file = DataFrameAppendFile()
    self.get_df = get_df
  
  def handle_record(self, record: Dict):
    self.records.append(record)
    self.try_save()
  
  def try_save(self):
    time_now = time.time()
    time_diff = time_now - self.last_save
    if time_diff > self.seconds_between_save:
      self.save_immediately()
  
  def get_df_to_save(self) -> Optional[pd.DataFrame]:
    if len(self.records) > 0:
      df = StepsRunTimesStore.to_dataframe(self.records)
      self.records = []
      return df
    
    if self.get_df is not None:
      return self.get_df()

    return None

  def save_immediately(self):
    df = self.get_df_to_save()
    if df is None or len(df) == 0:
      return

    self.last_save = time.time()

    if self.should_append:
      self.data_frame_append_file.save_dataframe(df, self.filepath)
    else:
      df.to_csv(self.filepath, index=False)

class WorkersMetadataManager:
  def __init__(self, worker_directory: str, WorkerMetadataClass: Optional[Type[WorkerMetadata]] = None) -> None:
    if WorkerMetadataClass is not None:
      self.WorkerMetadataClass = WorkerMetadataClass
    else:
      self.WorkerMetadataClass = WorkerMetadata

    self.workers_metadata = {}
    self.worker_directory = worker_directory
    self.full_directory_path = os.path.join(WORKER_METADATA_DIRECTORY, worker_directory)
    ensure_directory_exists(self.full_directory_path)
    self.inputs_completed = 0
    self.time_passed_all_jobs = 0
    self.steps_run_times_store = StepsRunTimesStore()
    self.df_append_file = DataFrameAppendFile()

    self.df_throttle_save_all_steps = DataFrameThrottleSave(os.path.join(self.full_directory_path, 'steps_stats_all.csv'), get_df=lambda: self.steps_run_times_store.all_dataframe)
    self.df_throttle_save_current_steps = DataFrameThrottleSave(os.path.join(self.full_directory_path, 'steps_stats.csv'), should_append=True)
    self.all_throttle_saves = [
      self.df_throttle_save_all_steps,
      self.df_throttle_save_current_steps,
    ]
  
  def save_all(self):
    for throttle_save in self.all_throttle_saves:
      throttle_save.save_immediately()
  
  def get_worker_metadata(self, worker_number: int) -> WorkerMetadata:
    if not worker_number in self.workers_metadata:
      self.workers_metadata[worker_number] = self.WorkerMetadataClass(worker_number=worker_number)
    return self.workers_metadata[worker_number]
  

  def create_all_workers_dataframe(self) -> pd.DataFrame:
    workers_metadata = list(self.workers_metadata.values())

    return create_workers_dataframe(workers_metadata)
  
  # TODO: Throttle
  def save_job_complete_metadata(self, worker_number):
    worker_metadata = self.get_worker_metadata(worker_number)
    df = create_workers_dataframe([worker_metadata])
    full_path = os.path.join(self.full_directory_path, 'jobs_completed.csv')

    self.df_append_file.save_dataframe(df, full_path)

  # TODO: Throttle
  def save_current_workers_metadata(self):
    df = self.create_all_workers_dataframe()
    full_path = os.path.join(self.full_directory_path, 'workers_metadata.csv')
    df.to_csv(full_path, index=False)
  
  def update_worker_metadata(self, worker_number, **kwargs):
    self.get_worker_metadata(worker_number).update(**kwargs)
    self.save_current_workers_metadata()

  def handle_step_change(self, worker_number, step_number, step_description):
    worker_metadata = self.get_worker_metadata(worker_number)
    average_run_time_for_step, last_time_passed = worker_metadata.on_step_change(step_number, step_description)

    if average_run_time_for_step is not None and last_time_passed is not None:
      self.steps_run_times_store.set_step_run_time(step_description, average_run_time_for_step, last_time_passed, step_number)
      self.df_throttle_save_all_steps.try_save()
      self.df_throttle_save_current_steps.handle_record(self.steps_run_times_store.dict_from_description(step_description))
  
  def handle_worker_finished(self, worker_number):
    self.get_worker_metadata(worker_number).on_complete()
    self.save_current_workers_metadata()

  def handle_input_start(self, worker_number):
    self.get_worker_metadata(worker_number).on_input_start()
    self.save_current_workers_metadata()

  def handle_input_end(self, worker_number) -> Optional[float]:
    worker_metadata = self.get_worker_metadata(worker_number)
    time_passed = worker_metadata.on_input_end()
    if time_passed is None:
      return None
    self.save_job_complete_metadata(worker_number)
    self.save_current_workers_metadata()

    self.time_passed_all_jobs += time_passed
    self.inputs_completed += 1

    average_time_completion_for_input = self.time_passed_all_jobs / self.inputs_completed

    return average_time_completion_for_input

  def handle_input_error(self, worker_number):
    self.get_worker_metadata(worker_number).update(error=True)
    self.save_job_complete_metadata(worker_number)
    self.save_current_workers_metadata()
