import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

class MLSEngine:
    def __init__(self, username):
        self.username = username
        # In a real MLS setup, this is an ephemeral HPKE key. 
        # We use RSA here for structural demonstration.
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        
    def generate_key_package(self):
        """Creates the MLS KeyPackage: The public key signed by the user's Identity."""
        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        # We encode it in base64 so it can be safely transmitted over the pipe-separated QUIC stream
        return base64.b64encode(pub_bytes).decode('utf-8')

    def encrypt_message(self, target_key_package, plaintext):
        """Encrypts a message so only the target can read it (End-to-End Encryption)."""
        target_pub_bytes = base64.b64decode(target_key_package)
        target_pub_key = serialization.load_pem_public_key(target_pub_bytes)
        
        ciphertext = target_pub_key.encrypt(
            plaintext.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(ciphertext).decode('utf-8')

    def decrypt_message(self, ciphertext_b64):
        """Decrypts an incoming message using the local private key."""
        ciphertext = base64.b64decode(ciphertext_b64)
        plaintext = self.private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext.decode('utf-8')
