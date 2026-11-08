"""Small, dependency-free BLAKE3 implementation for the Pages uploader.

Cloudflare's Pages Direct Upload API identifies assets by the same
content hash Wrangler computes: BLAKE3(base64(file bytes) + extension),
truncated to 32 hex characters.  The site has no third-party build
dependencies, so this module keeps the hashing step self-contained.

Only the 32-byte default output is needed.  The implementation follows the
BLAKE3 specification (chunk size 1024, block size 64, seven rounds).
"""

from __future__ import annotations

IV = [
    0x6A09E667,
    0xBB67AE85,
    0x3C6EF372,
    0xA54FF53A,
    0x510E527F,
    0x9B05688C,
    0x1F83D9AB,
    0x5BE0CD19,
]
MSG_PERMUTATION = [2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8]
CHUNK_START = 1
CHUNK_END = 2
PARENT = 4
ROOT = 8
MASK = 0xFFFFFFFF


def _rotr(value: int, count: int) -> int:
    return ((value >> count) | (value << (32 - count))) & MASK


def _g(state: list[int], a: int, b: int, c: int, d: int, x: int, y: int) -> None:
    state[a] = (state[a] + state[b] + x) & MASK
    state[d] = _rotr(state[d] ^ state[a], 16)
    state[c] = (state[c] + state[d]) & MASK
    state[b] = _rotr(state[b] ^ state[c], 12)
    state[a] = (state[a] + state[b] + y) & MASK
    state[d] = _rotr(state[d] ^ state[a], 8)
    state[c] = (state[c] + state[d]) & MASK
    state[b] = _rotr(state[b] ^ state[c], 7)


def _round(state: list[int], message: list[int]) -> None:
    _g(state, 0, 4, 8, 12, message[0], message[1])
    _g(state, 1, 5, 9, 13, message[2], message[3])
    _g(state, 2, 6, 10, 14, message[4], message[5])
    _g(state, 3, 7, 11, 15, message[6], message[7])
    _g(state, 0, 5, 10, 15, message[8], message[9])
    _g(state, 1, 6, 11, 12, message[10], message[11])
    _g(state, 2, 7, 8, 13, message[12], message[13])
    _g(state, 3, 4, 9, 14, message[14], message[15])


def _words(block: bytes) -> list[int]:
    return [int.from_bytes(block[i : i + 4], "little") for i in range(0, 64, 4)]


def _compress(
    chaining_value: list[int],
    block_words: list[int],
    counter: int,
    block_len: int,
    flags: int,
) -> list[int]:
    state = list(chaining_value) + IV[:4] + [
        counter & MASK,
        (counter >> 32) & MASK,
        block_len,
        flags,
    ]
    message = list(block_words)
    for round_index in range(7):
        _round(state, message)
        if round_index != 6:
            message = [message[i] for i in MSG_PERMUTATION]
    for i in range(8):
        state[i] ^= state[i + 8]
        state[i + 8] ^= chaining_value[i]
    return state


def _chunk_output(chunk: bytes, counter: int, root: bool) -> list[int]:
    chaining_value = list(IV)
    blocks = [chunk[i : i + 64] for i in range(0, len(chunk), 64)] or [b""]
    for index, block in enumerate(blocks):
        flags = CHUNK_START if index == 0 else 0
        if index == len(blocks) - 1:
            flags |= CHUNK_END
            if root:
                flags |= ROOT
        padded = block + b"\x00" * (64 - len(block))
        output = _compress(
            chaining_value,
            _words(padded),
            counter,
            len(block),
            flags,
        )
        if root and index == len(blocks) - 1:
            return output[:8]
        chaining_value = output[:8]
    return chaining_value


def _parent_output(left: list[int], right: list[int], root: bool) -> list[int]:
    block = b"".join(
        word.to_bytes(4, "little") for word in (left + right)
    )
    return _compress(IV, _words(block), 0, 64, PARENT | (ROOT if root else 0))


def blake3(data: bytes) -> bytes:
    """Return the 32-byte BLAKE3 digest of *data*."""
    if len(data) <= 1024:
        output = _chunk_output(data, 0, True)
        return b"".join(word.to_bytes(4, "little") for word in output)

    chunks = [data[i : i + 1024] for i in range(0, len(data), 1024)]
    chaining_values = [
        _chunk_output(chunk, index, False) for index, chunk in enumerate(chunks)
    ]
    while len(chaining_values) > 2:
        next_level: list[list[int]] = []
        for index in range(0, len(chaining_values) - 1, 2):
            next_level.append(
                _parent_output(
                    chaining_values[index], chaining_values[index + 1], False
                )[:8]
            )
        if len(chaining_values) % 2:
            next_level.append(chaining_values[-1])
        chaining_values = next_level
    output = _parent_output(chaining_values[0], chaining_values[1], True)
    return b"".join(word.to_bytes(4, "little") for word in output[:8])


def pages_hash(path: str) -> str:
    """Return the 32-character hash Wrangler uses in a Pages manifest."""
    import base64
    import os
    import pathlib

    raw = pathlib.Path(path).read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    extension = os.path.splitext(path)[1][1:]
    return blake3((encoded + extension).encode("ascii")).hex()[:32]


def _self_test() -> None:
    vectors = {
        b"": "af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262",
        b"abc": "6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85",
        b"hello world": "d74981efa70a0c880b8d8c1985d075dbcbf679b99a5f9914e5aaf96b831a9e24",
    }
    for data, expected in vectors.items():
        actual = blake3(data).hex()
        if actual != expected:
            raise SystemExit(f"BLAKE3 self-test failed for {data!r}: {actual}")


if __name__ == "__main__":
    _self_test()
    print("BLAKE3 self-test passed")
