from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64

private_key = RSA.generate(2048)
public_key = private_key.publickey()
cipher = PKCS1_OAEP.new(private_key)

def get_public_key():
    return public_key.export_key().decode()

def decrypt_data(encrypted_data):
    return cipher.decrypt(base64.b64decode(encrypted_data)).decode()
