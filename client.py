import asyncio
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration

async def send_telemetry_data(protocol, stream_id):
    # Simulates sneding continuous sensor data on Channel 1
    counter = 1
    while True:
        message = f"Telemetry packet {counter}".encode("utf-8")

        # Queue the data in the local machine
        protocol._quic.send_stream_data(stream_id, message, end_stream=False)

        protocol.transmit()

        print(f"[Channel {stream_id} Sent: {message.decode('utf-8')}")
        counter += 1
        await asyncio.sleep(1) # Sends once per second

async def send_log_data(protocol, stream_id):
    # Simulates sending intermittent data on Channel 2
    counter = 1
    while True:
        message = f"Log entry {counter}: System stable.".encode('utf-8')

        protocol._quic.send_stream_data(stream_id, message, end_stream=False)
        protocol.transmit()

        print(f"[Channel {stream_id}] Sent: {message.decode('utf-8')}")
        counter += 1
        await asyncio.sleep(2.5) # Sends once every 2.5 seconds

async def main():
    configuration = QuicConfiguration(is_client=True, verify_mode=False)

    server_ip = "192.168.0.20"

    print(f"Connecting to {server_ip}:4433 over QUIC...")

    async with connect(server_ip, 4433, configuration=configuration) as protocol:
        print("Connection established!")

        channel_1_id = protocol._quic.get_next_available_stream_id()
        channel_2_id = channel_1_id + 4

        await asyncio.gather(
                send_telemetry_data(protocol, channel_1_id),
                send_log_data(protocol, channel_2_id)
                )
if __name__ == "__main__":
    asyncio.run(main())
