from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import os

# Generate shared key using X25519
private_key = x25519.X25519PrivateKey.generate()
public_key = private_key.public_key()
peer_private = x25519.X25519PrivateKey.generate()
shared_key = private_key.exchange(peer_private.public_key())

def derive_aes_key(shared_secret):
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'chat-key'
    ).derive(shared_secret)

aes_key = derive_aes_key(shared_key)

def encrypt_message(plaintext):
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
    return iv + ciphertext

def decrypt_message(ciphertext):
    iv = ciphertext[:16]
    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv))
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext[16:]) + decryptor.finalize()
    return plaintext.decode()
