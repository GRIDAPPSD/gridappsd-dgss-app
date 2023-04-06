import logging
import sys

from kafka import KafkaProducer

root = logging.getLogger()
root.setLevel(logging.DEBUG) 

handler = logging.StreamHandler(sys.stdout) 
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s') 
handler.setFormatter(formatter) 
root.addHandler(handler)

producer = KafkaProducer(bootstrap_servers='localhost:31402')
for _ in range(100):
    print('sending message')
    producer.send('my-topic', b'some_message_bytes')
producer.flush()

print('done')