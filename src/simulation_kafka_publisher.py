import argparse
import json
import logging
import sys
import time

from kafka import KafkaProducer
from gridappsd import GridAPPSD, DifferenceBuilder, utils
from gridappsd.topics import simulation_input_topic, simulation_output_topic, simulation_log_topic, \
    simulation_output_topic

root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)
consumer_topic = 'my-topic'

producer = KafkaProducer(bootstrap_servers='localhost:31402')


DEFAULT_MESSAGE_PERIOD = 5

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
#                     format="%(asctime)s - %(name)s;%(levelname)s|%(message)s",
#                     datefmt="%Y-%m-%d %H:%M:%S")
# Only log errors to the stomp logger.
logging.getLogger('stomp.py').setLevel(logging.ERROR)

_log = logging.getLogger(__name__)


class SimulationMessages():

    def __init__(self, simulation_id, gridappsd_obj):

        self._gapps = gridappsd_obj

        self._message_count = 0

    def on_message(self, headers, message):
        self.send_message(message)


    def send_message(self, message):
        # Send message to Kafka consumer
        producer.send(consumer_topic, json.dumps(message).encode('utf-8'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('simulation_id', help="Simulation id")
    opts = parser.parse_args()
    simulation_id = opts.simulation_id
    listening_to_topic = simulation_output_topic(opts.simulation_id)
    gapps = GridAPPSD(opts.simulation_id)

    simulation = SimulationMessages(simulation_id, gapps)

    gapps.subscribe(listening_to_topic, simulation)
    while True:
        time.sleep(0.1)

