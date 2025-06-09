import pickle
from typing import Optional, Any, TypeVar, Union, Iterator, Generic

import lmdb


DType = TypeVar("DType")
DefaultType = TypeVar("DefaultType")


PROBE_BIT_WIDTH = 2


class KVModel(Generic[DType]):
    def __init__(
        self,
        db,
        namespace,
        kind,
        extra_index: Optional[list[str]] = None,
    ):
        self.db = db
        self.namespace = namespace
        self.kind = kind
        self.extra_index = extra_index or []

    @classmethod
    def _db_range_read(cls, txn, start_key: bytes, end_key: bytes):
        with txn.cursor() as cursor:
            cursor.set_range(start_key)
            for k, v in cursor:
                if k >= end_key:
                    break
                yield pickle.loads(v)

    def db_key(
        self,
        entity_index: str,
        entity_id: str,
    ) -> bytes:
        return f"{self.namespace}.{self.kind}.{entity_index}.{entity_id}".encode()

    def put(self, id: str, data: DType, override: bool = True) -> bytes:
        with self.db.begin(write=True) as txn:
            key = self.db_key("by_id", id)
            if txn.get(key):
                if not override:
                    return key
                else:
                    txn.put(key, pickle.dumps(data))
                    return key

            txn.put(key, pickle.dumps(data))

            if isinstance(data, dict):
                for index in self.extra_index:
                    value = data.get(index)
                    if value is None:
                        continue
                    for i in range(10**PROBE_BIT_WIDTH):
                        suffix = str(i).zfill(PROBE_BIT_WIDTH)
                        key = self.db_key(
                            f"by_{index}",
                            f"{value}_{suffix}",
                        )
                        if not txn.get(key):
                            txn.put(key, pickle.dumps(id))
                            break
            return key

    def get(self, id: str, default: DefaultType = None) -> Union[DType, DefaultType]:
        with self.db.begin() as txn:
            key = self.db_key("by_id", id)
            data = txn.get(key)
            if data:
                return pickle.loads(data)
        return default

    def iter_by(self, index: str, begin: Any, end: Any) -> Iterator[tuple[str, DType]]:
        min_num = str(0).zfill(PROBE_BIT_WIDTH)
        max_num = str(10**PROBE_BIT_WIDTH - 1).zfill(PROBE_BIT_WIDTH)
        with self.db.begin() as txn:
            for v in self._db_range_read(
                txn,
                self.db_key(f"by_{index}", f"{begin}_{min_num}"),
                self.db_key(
                    f"by_{index}",
                    f"{end}_{max_num}",
                ),
            ):
                key = self.db_key("by_id", v)
                value = txn.get(key)
                if not value:
                    continue
                yield v, pickle.loads(value)


if __name__ == "__main__":
    import time

    # Example usage
    test_db = lmdb.open("/tmp/test_db", map_size=100 * 1024**2)
    kv_model = KVModel(test_db, "namespace", "kind", ["timestamp"])
    now = int(time.time())
    for i in range(10):
        key = kv_model.put(str(i), {"id": str(i), "timestamp": now})
        print(key, i)

    item = kv_model.get("1")
    print(item)
    assert item
    assert item.get("id") == "1"

    for i, item in kv_model.iter_by_index("timestamp", now, now + 1):
        print(i, item)
        assert item.get("id") == str(i)

    test_db.close()

    # Cleanup
    import shutil

    shutil.rmtree("/tmp/test_db")
