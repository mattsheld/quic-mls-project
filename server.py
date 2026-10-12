import asyncio
from aioquic.asyncio import serve, QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived

# 1. The Event Handler
class MultiplexServerProtocol(QuicConnectionProtocol):
    def quic_event_received(self, event):
        # aioquic parses the raw UDP packets in the background. 
        # When it pieces together a complete application message, it fires this event.
        
        if isinstance(event, StreamDataReceived):
            # The data arrives as raw bytes, so we decode it to a string
            message = event.data.decode('utf-8')
            
            # The stream_id is how we multiplex. The client will send data on two 
            # different IDs over the single UDP connection.
            channel_id = event.stream_id
            
            print(f"[Channel {channel_id} Received] {message}")

async def main():
    # 2. The Configuration
    # We tell aioquic this is a server, and feed it the certs you just generated.
    configuration = QuicConfiguration(is_client=False)
    configuration.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

    print("Starting QUIC server on 0.0.0.0:4433...")
    
    # 3. Binding the Socket
    # 'serve' binds to UDP port 4433. When a client connects, it spawns an 
    # instance of MultiplexServerProtocol to handle that specific client's events.
    await serve(
        host="0.0.0.0",
        port=4433,
        configuration=configuration,
        create_protocol=MultiplexServerProtocol,
    )
    
    # 4. Keeping it Alive
    # Because serve() runs in the background, we need an infinite future to 
    # prevent the Python script from immediately exiting.
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
