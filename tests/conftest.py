import os
import tempfile
from pathlib import Path

# Never point destructive test fixtures at a developer's configured database.
_test_directory = tempfile.TemporaryDirectory(prefix="chatlens-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_test_directory.name) / "test.db")
