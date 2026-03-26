__all__ = [
    "__version__",
    "Array",
    "ChunkedArray",
    "RecordBatch",
    "Scalar",
    "Table",
]

# Provide a minimal stub so libraries that probe for pyarrow can import it
# without loading the blocked site-packages wheel on this machine.
__version__ = "0.0.0"


class Array:
    pass


class ChunkedArray:
    pass


class RecordBatch:
    pass


class Scalar:
    pass


class Table:
    pass
