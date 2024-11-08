import time
import json
import logging
import asyncio
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

from aiortc import RTCDataChannel, VideoStreamTrack

from signaling_utils import WebRTCClient, receive_signaling
from settings import *


class StationClient(WebRTCClient):
    def __init__(self, signaling_server_url: str, room_id: str) -> None:
        super().__init__(signaling_server_url, room_id)
        self.data_channel: RTCDataChannel = None
        self.producer_queue: Queue = None
        self.consumer_queue: Queue = None
        self.loop: asyncio.AbstractEventLoop = None

    def __setup_datachannel_callbacks(self) -> None:
        @self.pc.on("datachannel")
        async def on_datachannel(channel: RTCDataChannel) -> None:
            self.data_channel = channel

            @self.data_channel.on("open")
            def on_open() -> None:
                print("Data channel opened by Jackal")

            @self.data_channel.on("message")
            async def on_message(message: str) -> None:
                await self.loop.run_in_executor(None, self.consumer_queue.put, message) 
                self.consumer_queue.task_done()   

            @self.data_channel.on("close")
            def on_close() -> None:
                print("Data channel closed by Jackal")

    async def run(self) -> None:
        await super().run()
        self.__setup_datachannel_callbacks()
        await receive_signaling(self.pc, self.signaling)

        await self.done.wait()
        await self.pc.close()
        await self.signaling.close()
        print("Workstation client stopped")

    def set_producer_queue(self, queue: Queue) -> None:
        self.producer_queue = queue

    def set_consumer_queue(self, queue: Queue) -> None:
        self.consumer_queue = queue

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop


def mock_syncronize_manager(consumer_queue: Queue, event: asyncio.Event) -> None:
    while not event.is_set():
        if consumer_queue.qsize() == 0:
            time.sleep(0.001)
            continue

        data: bytes = consumer_queue.get()
        item_from_peer: dict = json.loads(data)
        print(f"Received Jackal's message: {item_from_peer}")


def empty_queue(queue: Queue) -> None:
    print(f"Emptying queue with {queue.qsize()} elements")
    while queue.qsize() > 0:
        queue.get()
    print(f"Current queue size is {queue.qsize()}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    receiver: StationClient = StationClient(IP, PORT)
    executor = ThreadPoolExecutor(max_workers=1)
    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    producer_queue, consumer_queue = Queue(maxsize=10), Queue(maxsize=10)    

    try:
        receiver.set_loop(loop)
        receiver.set_producer_queue(producer_queue)
        receiver.set_consumer_queue(consumer_queue)

        loop.run_in_executor(executor, mock_syncronize_manager, consumer_queue, receiver.done)
        loop.run_until_complete(receiver.run())
    except KeyboardInterrupt:
        print("User interrupted the program")
    except Exception as e:
        print(f"Exception occurred: {e}")
    finally:
        print("Closing the program...")
        receiver.done.set()
        empty_queue(producer_queue)
        empty_queue(consumer_queue)

        loop.close()   
        executor.shutdown()
