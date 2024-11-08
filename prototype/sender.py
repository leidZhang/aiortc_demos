import asyncio
import json
import base64
import logging

import cv2
import numpy as np
from aiortc import RTCPeerConnection, RTCConfiguration, RTCIceServer
from aiortc.contrib.signaling import TcpSocketSignaling


def encode_image(image: np.ndarray, extension: str = '.jpg') -> str:
    _, buffer = cv2.imencode(extension, image)
    return base64.b64encode(buffer).decode('utf-8')


async def send_dict():
    logging.basicConfig(level=logging.INFO)
    pc = RTCPeerConnection()
    channel = pc.createDataChannel('data')

    async def send_data():
        data = {"image": encode_image(np.random.randint(0, 255, size=(480, 640, 3), dtype=np.uint8))}
        channel.send(json.dumps(data))
        print("Data sent to the receiver")

    @channel.on('open')
    async def on_open():
        logging.info("Data channel opened")
        await send_data()

    signaling = TcpSocketSignaling('localhost', 1234)
    await signaling.connect()
    logging.info("Connected to signaling server")

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    await signaling.send(pc.localDescription)
    logging.info("Offer sent to signaling server")

    answer = await signaling.receive()
    await pc.setRemoteDescription(answer)

    await asyncio.sleep(10) 


if __name__ == '__main__':
    asyncio.run(send_dict())
