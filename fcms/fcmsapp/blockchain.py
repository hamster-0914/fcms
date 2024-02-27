import hashlib
import json


class Block:
     def __init__(self, index, timestamp, previous_hash, data, hash):
          self.index = index
          self.timestamp = timestamp
          self.previous_hash = previous_hash
          self.data = data
          self.hash = hash

     def calculate_hash(self):
          data_string = json.dumps(self.data, sort_keys=True)
          return hashlib.sha256((str(self.timestamp) + str(self.previous_hash) + str(data_string)).encode('utf-8')).hexdigest()

     def is_valid(self):
          return self.hash == self.calculate_hash()

class Blockchain:
     # constructor
     def __init__(self, model, name):
          self.model = model
          self.name = name
          self.chain = []

     def load_from_db(self):
          blocks = self.model.objects.order_by('timestamp')
          previous_hash = "0" # genesis hash

          for block_data in blocks:
               # retrieve the model and change to block class
               # to do in memory 
               block = Block(block_data.index, block_data.timestamp, block_data.previous_hash, block_data.data, block_data.hash)
               if previous_hash != block.previous_hash:
                    return block.index # know which block got error

               if not block.is_valid():
                    return block.index 

               self.chain.append(block)
               previous_hash = block.hash
          return None