import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

class Reader(object):
    def __init__(self, file_path):
        self.file_path_ = file_path

    def read(self, format='PEM'):
        private_key_file = open(self.file_path_, 'rb')
        private_key = RSA.importKey(private_key_file.read())
        public_key = private_key.publickey()
        return private_key.exportKey(format), public_key.exportKey(format)


def write_key(file_path, key_data):
    key_file = open(file_path, 'wb')
    key_file.write(key_data)
    key_file.close()


class Generator(object):
    def __init__(self, bits_length=1024):
        self.bits_length_ = bits_length

    def generate(self, format='PEM'):
        random_gen = Crypto.Random.new().read
        private_key = RSA.generate(self.bits_length_, random_gen)
        public_key = private_key.publickey()
        return private_key.exportKey(format), public_key.exportKey(format)


class Writer(object):
    def __init__(self, file_path):
        self.file_path_ = file_path

    def write(self, key_data):
        return write_key(self.file_path_, key_data)


class Verify(object):
    def __init__(self, public_key: str):
        self.public_key_ = public_key

    def public_key(self) -> str:
        return self.public_key_

    def verify(self, data: bytes, signature: str) -> bool:
        """
        Check that the provided signature corresponds to data
        signed by the public key
        """
        public_key = RSA.importKey(self.public_key_)
        verifier = PKCS1_v1_5.new(public_key)

        h = SHA.new(data)
        return verifier.verify(h, signature)


class Sign(Verify):
    def __init__(self, public_key: str, private_key: str):
        Verify.__init__(self, public_key)
        self.private_key_ = private_key

    def sign(self, data: bytes) -> str:
        """
        Sign data with private key
        """
        private_key = RSA.importKey(self.private_key_)
        signer = PKCS1_v1_5.new(private_key)
        h = SHA.new(data)
        return signer.sign(h)
