import base64
import json
import hmac
import bcrypt
from hashlib import sha256
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import phpserialize  # For PHP deserialization
from BUDjangoProxy.settings import env_values


class LaravelEncryptor:
    def __init__(self, app_key=env_values['LARAVEL_APP_KEY']):
        # Ensure the key is 32 bytes long
        if len(app_key) < 32:
            # Pad the key with null bytes if it's too short
            self.key = app_key.ljust(32, '\x00')
        elif len(app_key) > 32:
            # Truncate the key if it's too long
            self.key = app_key[:32]
        else:
            self.key = app_key
        # Convert the key to bytes
        self.key = self.key.encode('utf-8')

    def encrypt(self, plain_text):
        # Generate a random 16-byte IV
        iv = b'\x00' * 16  # For simplicity, you can use a fixed IV or generate a random one
        # Create the AES cipher
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        # Pad the plaintext to be a multiple of 16 bytes
        padded_data = pad(phpserialize.dumps(plain_text.encode('utf-8')), AES.block_size)
        # Encrypt the data
        encrypted_data = cipher.encrypt(padded_data)
        # Base64 encode the IV and encrypted data
        iv_b64 = base64.b64encode(iv).decode('utf-8')
        value_b64 = base64.b64encode(encrypted_data).decode('utf-8')
        # Generate the MAC (HMAC-SHA256 of the IV + encrypted data)
        mac = self._generate_mac(iv_b64, value_b64)
        # Create the payload
        payload = {
            "iv": iv_b64,
            "value": value_b64,
            "mac": mac,
        }
        # Base64 encode the payload
        return base64.b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')

    def decrypt(self, encrypted_text):
        # Decode the base64-encoded encrypted text
        payload = json.loads(base64.b64decode(encrypted_text).decode('utf-8'))
        # Extract the IV, value, and MAC
        iv_b64 = payload["iv"]
        value_b64 = payload["value"]
        mac = payload["mac"]
        # Verify the MAC
        if not self._verify_mac(iv_b64, value_b64, mac):
            raise ValueError("Invalid MAC. The data may have been tampered with.")
        # Decode the IV and encrypted data
        iv = base64.b64decode(iv_b64)
        encrypted_data = base64.b64decode(value_b64)
        # Create the AES cipher
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        # Decrypt the data
        decrypted_data = cipher.decrypt(encrypted_data)
        # Unpad the decrypted data
        unpadded_data = unpad(decrypted_data, AES.block_size).decode('utf-8')
        # Deserialize the PHP-serialized string
        deserialized_data = phpserialize.loads(unpadded_data.encode('utf-8'))
        # Return the deserialized value
        return deserialized_data.decode('utf-8') if isinstance(deserialized_data, bytes) else deserialized_data

    def hashMaker(self, secret):
        # Convert secret to bytes
        password = secret.encode('utf-8')
        salt = bcrypt.gensalt(rounds=10, prefix=b'2a')
        hashed = bcrypt.hashpw(password, salt)
        return hashed.decode('utf-8')

    def _generate_mac(self, iv_b64, value_b64):
        # Generate the MAC (HMAC-SHA256 of the IV + encrypted data)
        mac_data = iv_b64 + value_b64
        return hmac.new(self.key, mac_data.encode('utf-8'), sha256).hexdigest()

    def _verify_mac(self, iv_b64, value_b64, mac):
        # Verify the MAC
        expected_mac = self._generate_mac(iv_b64, value_b64)
        return hmac.compare_digest(expected_mac, mac)