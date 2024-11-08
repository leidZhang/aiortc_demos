import json
import asyncio
import logging
from typing import Set

import websockets
from websockets import WebSocketServerProtocol

from settings import *

clients: Set[WebSocketServerProtocol] = set()


async def handler(websocket: WebSocketServerProtocol, path):
    # Register client
    clients.add(websocket)
    logging.info(f"New client {id(websocket)} connected")

    try:
        async for message in websocket:
            data = json.loads(message)
            # Broadcast the message to all connected clients except the sender
            for client in clients:
                if client != websocket:
                    logging.info("Starting signaling exchange...")
                    await client.send(json.dumps(data))
                    logging.info("Signaling exchange complete")
            logging.info(f"Peers have established a connection, unregistering...")
    except websockets.exceptions.ConnectionClosedError as e:
        logging.error(f"Connection closed with error: {e}")
    except websockets.exceptions.ConnectionClosedOK:
        logging.error("Connection closed normally")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        # Unregister client
        clients.remove(websocket)
        await websocket.close()


async def main():
    async with websockets.serve(handler, IP, PORT):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
