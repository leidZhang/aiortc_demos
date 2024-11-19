import logging
import asyncio

import av
import cv2
import numpy as np
from aiortc import RTCDataChannel, VideoStreamTrack
from aiortc.mediastreams import MediaStreamError
from signaling_utils import WebRTCClient, receive_signaling
from settings import *


async def consume(track: VideoStreamTrack):
    while True:
        try:
            frame: av.VideoFrame = await track.recv()
            image: np.ndarray = frame.to_ndarray(format="bgr24")
            print(image[0][0])
            cv2.imshow("Video", image)
            cv2.waitKey(1)
        except MediaStreamError:
            return


class Consumer:
    def __init__(self) -> None:
        self.__tracks = {}

    def addTrack(self, track) -> None:
        if track not in self.__tracks:
            self.__tracks[track] = None

    async def start(self) -> None:
        for track, task in self.__tracks.items():
            if task is None:
                self.__tracks[track] = asyncio.ensure_future(consume(track))

    async def stop(self) -> None:
        for task in self.__tracks.values():
            if task is not None:
                task.cancel()
        self.__tracks = {}


class StationClient(WebRTCClient):
    def __init__(self, signaling_server_url: str, room_id: str) -> None:
        super().__init__(signaling_server_url, room_id)
        self.data_channel_event: asyncio.Event = asyncio.Event()
        self.data_channel: RTCDataChannel = None
        self.consumer: Consumer = None

    def __setup_track_callbacks(self) -> None:
        self.consumer = Consumer()

        @self.pc.on("track")
        async def on_track(track: VideoStreamTrack):
            print("Track received", track.kind)
            if track.kind == "video":
                self.consumer.addTrack(track)
                await self.consumer.start()

    async def run(self) -> None:
        await super().run()
        self.__setup_track_callbacks()
        await receive_signaling(self.pc, self.signaling)

        await self.done.wait()
        await self.pc.close()
        await self.signaling.close()


async def run_receiver() -> None:
    receiver: WebRTCClient = StationClient(IP, PORT)
    await receiver.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(run_receiver())
