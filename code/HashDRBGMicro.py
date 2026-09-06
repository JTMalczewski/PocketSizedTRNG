import _sha256

class HashDRBGMicro:
    def __init__(self):
        self.hash_len = 32
        self.seed_len = 55
        self.modulus = 1 << (self.seed_len * 8)

        self.V = 0
        self.C = 0
        self.reseed_counter = 0

    def _hash_df(self, input_string: bytes, no_of_bytes_to_return: int) -> bytes:
        temp = bytearray()
        counter = 1
        no_of_bits_to_return = no_of_bytes_to_return * 8
        bits_bytes = no_of_bits_to_return.to_bytes(4, 'big')

        while len(temp) < no_of_bytes_to_return:
            h = _sha256.sha256()
            h.update(bytes([counter]))
            h.update(bits_bytes)
            h.update(input_string)
            temp.extend(h.digest())
            counter += 1

        return bytes(temp[:no_of_bytes_to_return])

    def instantiate(self, entropy: bytes, nonce: bytes = b"", personalization_string: bytes = b""):
        seed_material = entropy + nonce + personalization_string

        seed = self._hash_df(seed_material, self.seed_len)
        self.V = int.from_bytes(seed, 'big')

        c_input = b'\x00' + seed
        c_bytes = self._hash_df(c_input, self.seed_len)
        self.C = int.from_bytes(c_bytes, 'big')

        self.reseed_counter = 1

    def reseed(self, entropy: bytes, additional_input: bytes = b""):
        seed_material = (b'\x01' +
                         self.V.to_bytes(self.seed_len, 'big') +
                         entropy +
                         additional_input)

        seed = self._hash_df(seed_material, self.seed_len)
        self.V = int.from_bytes(seed, 'big')

        c_input = b'\x00' + seed
        c_bytes = self._hash_df(c_input, self.seed_len)
        self.C = int.from_bytes(c_bytes, 'big')

        self.reseed_counter = 1

    def _hash_gen(self, requested_bytes: int) -> bytes:
        m = (requested_bytes + self.hash_len - 1) // self.hash_len
        data = self.V
        W = bytearray()

        for _ in range(m):
            h = _sha256.sha256()
            h.update(data.to_bytes(self.seed_len, 'big'))
            W.extend(h.digest())
            data = (data + 1) % self.modulus

        return bytes(W[:requested_bytes])

    def generate(self, requested_bytes: int, additional_input: bytes = b"") -> bytes:
        if self.reseed_counter > 281474976710656:
            raise RuntimeError("Reseed required")

        if additional_input:
            h = _sha256.sha256()  # <-- Updated call
            h.update(b'\x02' + self.V.to_bytes(self.seed_len, 'big') + additional_input)
            w = int.from_bytes(h.digest(), 'big')
            self.V = (self.V + w) % self.modulus

        rnd_bytes = self._hash_gen(requested_bytes)

        h = _sha256.sha256()  # <-- Updated call
        h.update(b'\x03' + self.V.to_bytes(self.seed_len, 'big'))
        H = int.from_bytes(h.digest(), 'big')

        self.V = (self.V + H + self.C + self.reseed_counter) % self.modulus
        self.reseed_counter += 1

        return rnd_bytes
