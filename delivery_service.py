import asyncio
from aioquic.asyncio import serve, QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, ConnectionTerminated

# Central state for the Delivery Service
key_store = {}        # Maps "Username" -> "KeyPackage Bytes"
connected_clients = {} # Maps "Username" -> QuicConnectionProtocol

class MLSDeliveryServiceProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_name = None

    def quic_event_received(self, event):
        if isinstance(event, StreamDataReceived):
            # We assume messages are pipe-separated: COMMAND|TARGET|PAYLOAD
            raw_data = event.data.decode('utf-8', errors='ignore')
            parts = raw_data.split("|", 2)
            command = parts[0]

            if command == "REGISTER":
                # Client announces who they are: REGISTER|Alice|KeyPackageData
                self.client_name = parts[1]
                key_store[self.client_name] = parts[2]
                connected_clients[self.client_name] = self
                print(f"[*] Registered {self.client_name} and stored KeyPackage.")
                
                # Acknowledge registration
                self._quic.send_stream_data(event.stream_id, b"REGISTER_OK", end_stream=False)
                self.transmit()

            elif command == "FETCH":
                # Client requests someone's KeyPackage to start a group: FETCH|Bob
                target = parts[1]
                if target in key_store:
                    response = f"KEYPKG|{target}|{key_store[target]}".encode('utf-8')
                else:
                    response = b"ERROR|NOT_FOUND"
                self._quic.send_stream_data(event.stream_id, response, end_stream=False)
                self.transmit()

            elif command == "BROADCAST":
                # Client sends encrypted MLS message: BROADCAST|Bob|EncryptedBytes
                target = parts[1]
                ciphertext = parts[2]
                print(f"[>] Routing encrypted message from {self.client_name} to {target}")
                
                if target in connected_clients:
                    target_protocol = connected_clients[target]
                    # We open a new stream to push the data to the target
                    new_stream_id = target_protocol._quic.get_next_available_stream_id()
                    forward_msg = f"MLS_MSG|{self.client_name}|{ciphertext}".encode('utf-8')
                    target_protocol._quic.send_stream_data(new_stream_id, forward_msg, end_stream=False)
                    target_protocol.transmit()

        elif isinstance(event, ConnectionTerminated):
            if self.client_name and self.client_name in connected_clients:
                del connected_clients[self.client_name]
                print(f"[-] {self.client_name} disconnected.")

async def main():
    configuration = QuicConfiguration(is_client=False)
    # VM3 acts as the server, so it needs its own TLS cert. 
    # Use the same OpenSSL command you used before to generate a cert for VM3.
    configuration.load_cert_chain(certfile="vm3.pem", keyfile="vm3.key")

    print("Starting MLS Delivery Service on 0.0.0.0:4433...")
    await serve(
        host="0.0.0.0",
        port=4433,
        configuration=configuration,
        create_protocol=MLSDeliveryServiceProtocol,
    )
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
