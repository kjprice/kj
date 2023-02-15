
from typing import Dict, Optional

class MongoUpdate:
  def __init__(self, collection_name: str, query: Dict, update: Dict, upsert=False, update_many=False, finish_confirmation_key: Optional[str] = None) -> None:
    self.collection_name = collection_name
    self.query = query
    self.update = update
    self.upsert = upsert
    self.update_many = update_many
    self.finish_confirmation_key = finish_confirmation_key