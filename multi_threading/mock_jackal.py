import time
import json
import logging
import asyncio
import fractions
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple
from queue import Queue

import av
import cv2
import numpy as np
from aiortc import VideoStreamTrack, RTCDataChannel

from signaling_utils import WebRTCClient, initiate_signaling
from settings import *


class JackalClient(WebRTCClient):
    def __init__(self, signaling_ip: str, signaling_port: int) -> None:
        super().__init__(signaling_ip, signaling_port)
        self.data_channel: RTCDataChannel = None
        self.producer_queue: Queue = None
        self.consumer_queue: Queue = None
        self.loop: asyncio.AbstractEventLoop = None

    def __setup_datachannel_callbacks(self) -> None:
        self.data_channel = self.pc.createDataChannel("datachannel")

        @self.data_channel.on("open")
        async def on_open() -> None:
            print("Data channel opened")
            await self.__send_message()

        @self.data_channel.on("message")
        def on_message(message: str) -> None:
            print(f"Received message: {message}")

        @self.data_channel.on("close")
        def on_close() -> None:
            print("Data channel closed")

    async def __send_message(self) -> None:
        while True:
            item_from_producer: dict = await self.loop.run_in_executor(
                None, self.producer_queue.get
            )

            data: bytes = json.dumps(item_from_producer)
            self.data_channel.send(data)
            self.producer_queue.task_done()
            await asyncio.sleep(0.03) # about 25-30Hz
    
    async def run(self) -> None:
        await super().run()
        self.__setup_datachannel_callbacks()
        await initiate_signaling(self.pc, self.signaling)

        await self.done.wait()
        await self.pc.close()
        await self.signaling.close()
        print("Jackal client stopped")

    def set_producer_queue(self, queue: Queue) -> None:
        self.producer_queue = queue

    def set_consumer_queue(self, queue: Queue) -> None:
        self.consumer_queue = queue

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop


def mock_state_manager(producer_queue: Queue, event: asyncio.Event) -> None:
    from copy import deepcopy

    mock_state: dict = {"position": [1, 1, 1], "target": "Cat"}
    while not event.is_set():
        if producer_queue.full():
            producer_queue.get()
        producer_queue.put(deepcopy(mock_state))


def empty_queue(queue: Queue) -> None:
    print(f"Emptying queue with {queue.qsize()} elements")
    while queue.qsize() > 0:
        queue.get()
    print(f"Current queue size is {queue.qsize()}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    initiator: JackalClient = JackalClient(IP, PORT)
    executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1)
    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    producer_queue, consumer_queue = Queue(maxsize=10), Queue(maxsize=10)    

    try:
        initiator.set_loop(loop)
        initiator.set_producer_queue(producer_queue)
        initiator.set_consumer_queue(consumer_queue)

        loop.run_in_executor(executor, mock_state_manager, producer_queue, initiator.done)
        loop.run_until_complete(initiator.run())
    except KeyboardInterrupt:
        print("User interrupted the program")
    except Exception as e:
        print(f"Exception occurred: {e}")
    finally:
        print("Closing the program...")
        initiator.done.set()
        empty_queue(producer_queue)
        empty_queue(consumer_queue)
        
        loop.close()   
        executor.shutdown()
