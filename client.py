import asyncio
import websockets
import socket
import uuid

async def send_ip_and_mac_address():
    uri = "ws://localhost:8000/ws/"  # Replace with the actual WebSocket URI

    async with websockets.connect(uri) as websocket:
        ip_address = get_ip_address()
        mac_address = get_mac_address()
        data = {"ip_address": ip_address, "mac_address": mac_address}

        await websocket.send(str(data))
        print(f"Sent data to WebSocket: {data}")

        # Wait for messages from the server
        while True:
            try:
                message = await websocket.recv()
                print(f"Received message from server: {message}")
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed unexpectedly. Exiting.")
                break

def get_ip_address():
    # Get the local IP address of the machine
    ip_address = socket.gethostbyname(socket.gethostname())
    return ip_address

def get_mac_address():
    # Get the MAC address of the machine
    mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(5, -1, -1)])
    return mac_address

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(send_ip_and_mac_address())