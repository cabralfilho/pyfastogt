import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5


class Generator(object):
    def __init__(self, bits_length=1024):
        self.bits_length_ = bits_length

    def generate(self, format='PEM'):
        random_gen = Crypto.Random.new().read
        private_key = RSA.generate(self.bits_length_, random_gen)
        public_key = private_key.publickey()
        return private_key.exportKey(format), public_key.exportKey(format)


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
        Sign transaction with private key
        """
        private_key = RSA.importKey(self.private_key_)
        signer = PKCS1_v1_5.new(private_key)
        h = SHA.new(data)
        return signer.sign(h)
