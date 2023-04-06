import logging
import sys

from kafka import KafkaConsumer

#root = logging.getLogger()
#root.setLevel(logging.DEBUG) 

#handler = logging.StreamHandler(sys.stdout) 
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s') 
#handler.setFormatter(formatter) 
#root.addHandler(handler)

consumer = KafkaConsumer('my-topic',bootstrap_servers='localhost:31402')
for msg in consumer:
    print('here')
    print (msg)