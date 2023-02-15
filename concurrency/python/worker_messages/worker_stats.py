
from typing import Optional


class WorkerStats:
  worker_number = None
  def set_worker_number(self, worker_number: Optional[int]):
    self.worker_number = worker_number


class StepChangeStats(WorkerStats):
  def __init__(self, step_number: int, step_description: str) -> None:
    # TODO: Store how long step took
    self.step_number = step_number
    self.step_description = step_description

class WorkerFinishedStats(WorkerStats):
  pass

class WorkerMetadataInputStartStats(WorkerStats):
  pass

class WorkerMetadataInputEndStats(WorkerStats):
  pass

class WorkerMetadataInputErrorStats(WorkerStats):
  pass
