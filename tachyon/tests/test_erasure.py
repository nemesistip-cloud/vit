import pytest
from tachyon.core.erasure import ReedSolomonCodec
from app.core.errors import AppError

def test_encode_decode_roundtrip():
    codec = ReedSolomonCodec()
    data = b"Hello Tachyon VESS! This is a test of Reed-Solomon erasure coding."

    # Encode
    shards = codec.encode(data, data_shards=4, parity_shards=2)
    assert len(shards) == 6
    for s in shards:
        assert len(s) == len(shards[0])

    # Decode with all shards
    decoded = codec.decode(shards, data_shards=4, parity_shards=2)
    assert decoded[:len(data)] == data

def test_decode_with_missing_shards():
    codec = ReedSolomonCodec()
    data = b"Tachyon Protocol v5.5.0 - Shard Recovery Test"
    data_shards = 4
    parity_shards = 2

    shards = codec.encode(data, data_shards=data_shards, parity_shards=parity_shards)

    # 1 missing shard (data)
    shards_1 = list(shards)
    shards_1[0] = None
    assert codec.decode(shards_1, data_shards, parity_shards)[:len(data)] == data

    # 2 missing shards (data + parity)
    shards_2 = list(shards)
    shards_2[1] = None
    shards_2[4] = None
    assert codec.decode(shards_2, data_shards, parity_shards)[:len(data)] == data

def test_decode_with_max_parity_missing():
    codec = ReedSolomonCodec()
    data = b"Testing max parity missing shards"
    data_shards = 4
    parity_shards = 3

    shards = codec.encode(data, data_shards=data_shards, parity_shards=parity_shards)

    # 3 missing shards (all parity)
    shards_3 = list(shards)
    shards_3[4] = None
    shards_3[5] = None
    shards_3[6] = None
    assert codec.decode(shards_3, data_shards, parity_shards)[:len(data)] == data

    # 3 missing shards (all data)
    shards_3_data = list(shards)
    shards_3_data[0] = None
    shards_3_data[1] = None
    shards_3_data[2] = None
    assert codec.decode(shards_3_data, data_shards, parity_shards)[:len(data)] == data

def test_decode_fails_with_too_many_missing():
    codec = ReedSolomonCodec()
    data = b"Too many missing shards test"
    data_shards = 4
    parity_shards = 2

    shards = codec.encode(data, data_shards=data_shards, parity_shards=parity_shards)

    # 3 missing shards (parity is 2)
    shards_3 = list(shards)
    shards_3[0] = None
    shards_3[1] = None
    shards_3[2] = None

    with pytest.raises(AppError) as excinfo:
        codec.decode(shards_3, data_shards, parity_shards)
    assert "storage_unrecoverable" in str(excinfo.value)

def test_shard_hash_determinism():
    codec = ReedSolomonCodec()
    shard = b"some random shard data"
    hash1 = codec.shard_hash(shard)
    hash2 = codec.shard_hash(shard)
    assert hash1 == hash2
    assert len(hash1) == 64 # SHA-256 hex string length
