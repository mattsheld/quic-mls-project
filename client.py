import sys
import asyncio
from aioquic.asyncio import connect, QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived
from mls_engine import MLSEngine

class MLSClientProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mls = None
        self.target_key_package = None
        self.main_stream_id = None

    def quic_event_received(self, event):
        if isinstance(event, StreamDataReceived):
            raw_data = event.data.decode('utf-8', errors='ignore')
            parts = raw_data.split("|", 2)
            command = parts[0]

            if command == "KEYPKG":
                # Received the target's KeyPackage from VM3
                target_name = parts[1]
                self.target_key_package = parts[2]
                print(f"[+] Received KeyPackage for {target_name}. Ready to encrypt.")
            
            elif command == "MLS_MSG":
                # Received an end-to-end encrypted message from another client
                sender = parts[1]
                ciphertext = parts[2]
                print(f"[>] Raw Ciphertext from {sender}: {ciphertext[:20]}...")
                
                # Decrypt it locally
                plaintext = self.mls.decrypt_message(ciphertext)
                print(f"[!] DECRYPTED payload from {sender}: {plaintext}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 client.py <Username> [TargetToMessage]")
        sys.exit(1)
        
    username = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Initialize the Cryptographic Engine
    engine = MLSEngine(username)
    
    configuration = QuicConfiguration(is_client=True, verify_mode=False)
    server_ip = "192.168.0.20" # IMPORTANT: Change to VM3's actual IP

    print(f"Connecting to Delivery Service at {server_ip}...")
    
    async with connect(server_ip, 4433, configuration=configuration, create_protocol=MLSClientProtocol) as protocol:
        protocol.mls = engine
        stream_id = protocol._quic.get_next_available_stream_id()
        protocol.main_stream_id = stream_id
        
        # 1. Register with VM3
        key_package = engine.generate_key_package()
        reg_msg = f"REGISTER|{username}|{key_package}".encode('utf-8')
        protocol._quic.send_stream_data(stream_id, reg_msg, end_stream=False)
        protocol.transmit()
        print(f"[*] Sent KeyPackage to Delivery Service.")
        
        # 2. If a target is specified, fetch their key and send a message
        if target:
            await asyncio.sleep(1) # Give VM3 time to process registration
            
            fetch_msg = f"FETCH|{target}".encode('utf-8')
            protocol._quic.send_stream_data(stream_id, fetch_msg, end_stream=False)
            protocol.transmit()
            print(f"[*] Requesting {target}'s KeyPackage...")
            
            # Wait for the KeyPackage to arrive via the event handler
            while protocol.target_key_package is None:
                await asyncio.sleep(0.5)
                
            # Encrypt and send the payload
            secret_msg = "Classified telemetry data: Altitude 40,000ft."
            ciphertext = engine.encrypt_message(protocol.target_key_package, secret_msg)
            
            broadcast_msg = f"BROADCAST|{target}|{ciphertext}".encode('utf-8')
            protocol._quic.send_stream_data(stream_id, broadcast_msg, end_stream=False)
            protocol.transmit()
            print(f"[*] Sent E2EE message to {target}.")
            
        # Keep connection open to receive incoming messages
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
