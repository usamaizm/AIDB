"""The store must be safe to use from many threads at once.

Before this lane, AIDB held one SQLite connection shared by every thread
and the HTTP server serialized whole requests behind the connection
lock, so reads queued behind writes. The store now gives each thread its
own connection for file-backed homes and runs in WAL mode: readers
proceed concurrently with each other and with the single writer, while
compound mutations still serialize on the store's write lock. A
:memory: home deliberately keeps one shared connection — separate
connections would each see a different empty database.

The invariants asserted here: WAL is actually active, threads really do
get distinct connections, parallel writers and readers complete with no
lock errors and no lost updates, revision conflicts are still detected
when two writers race the same resource, :memory: stays one consistent
database across threads, reads never wait for the write lock, and
close() shuts down every thread's connection.
"""

import json
import sqlite3
from http.client import HTTPConnection
from threading import Barrier, Event, Thread

import pytest

from aidb import AIDB
from aidb.server import create_server


def test_file_backed_home_uses_wal_and_per_thread_connections(tmp_path):
    db = AIDB(tmp_path / "home.sqlite3")
    try:
        assert db.db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.db.execute("PRAGMA busy_timeout").fetchone()[0] == 5000

        main_connection = db.db
        seen = {}

        def probe():
            seen["connection"] = db.db
            seen["journal_mode"] = db.db.execute("PRAGMA journal_mode").fetchone()[0]

        worker = Thread(target=probe)
        worker.start()
        worker.join(timeout=5)
        assert not worker.is_alive()
        # A different thread gets its own connection to the same file,
        # already in WAL mode; repeated access within one thread is the
        # same object, so a call's statements stay on one connection.
        assert seen["connection"] is not main_connection
        assert seen["journal_mode"] == "wal"
        assert db.db is main_connection
    finally:
        db.close()


def test_reads_do_not_wait_for_the_write_lock(tmp_path):
    db = AIDB(tmp_path / "home.sqlite3")
    try:
        db.create_resource("item", {"value": 1})
        done = Event()
        errors = []

        def read():
            try:
                assert len(db.list_resources()) == 1
            except Exception as exc:  # surfaced by the assertion below
                errors.append(exc)
            finally:
                done.set()

        with db._connection_lock:
            worker = Thread(target=read)
            worker.start()
            # The read must complete while the write lock is held by
            # another thread; before per-thread connections, the HTTP
            # layer had to hold this lock across whole reads.
            assert done.wait(timeout=5)
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert errors == []
    finally:
        db.close()


def test_parallel_writers_and_readers_lose_nothing(tmp_path):
    writers_count = 4
    creates_per_writer = 15
    readers_count = 3
    db = AIDB(tmp_path / "home.sqlite3")
    try:
        start = Barrier(writers_count + readers_count + 1)
        writers_done = Event()
        errors = []
        created_ids = []

        def writer(index):
            start.wait()
            try:
                for i in range(creates_per_writer):
                    resource = db.create_resource("item", {"writer": index, "index": i})
                    created_ids.append(resource.id)
            except Exception as exc:  # surfaced by the assertion below
                errors.append(f"writer {index}: {type(exc).__name__}: {exc}")

        def reader(index):
            start.wait()
            try:
                while not writers_done.is_set():
                    db.list_resources()
                    payload = db.export_home()
                    assert "tables" in payload
            except Exception as exc:  # surfaced by the assertion below
                errors.append(f"reader {index}: {type(exc).__name__}: {exc}")

        writers = [Thread(target=writer, args=(i,)) for i in range(writers_count)]
        readers = [Thread(target=reader, args=(i,)) for i in range(readers_count)]
        for thread in writers + readers:
            thread.start()
        start.wait()
        for thread in writers:
            thread.join(timeout=30)
        writers_done.set()
        for thread in readers:
            thread.join(timeout=30)

        assert all(not t.is_alive() for t in writers + readers)
        assert errors == []
        expected = writers_count * creates_per_writer
        assert len(created_ids) == expected
        assert len(set(created_ids)) == expected
        rows = db.db.execute("SELECT COUNT(*), SUM(revision) FROM home_resources").fetchone()
        assert rows[0] == expected
        # Every create landed at revision 1: no update was lost into or
        # merged with another writer's row.
        assert rows[1] == expected
        changes = db.db.execute(
            "SELECT COUNT(*) FROM home_changes WHERE operation='create'"
        ).fetchone()[0]
        assert changes == expected
    finally:
        db.close()


def test_concurrent_update_conflict_still_detected_on_file_backed_home(tmp_path):
    # Invariant: two updates racing on the same expected_revision of a
    # file-backed home — exactly one applies; the loser gets a revision
    # conflict and the stored revision advances exactly once. Distinct
    # per-thread connections must not weaken the SQL-level guard.
    db = AIDB(tmp_path / "home.sqlite3")
    try:
        resource = db.create_resource("item", {"version": 1})
        barrier = Barrier(3)
        outcomes = []

        def update(value):
            barrier.wait()
            try:
                db.update_resource(resource.id, content={"version": value}, expected_revision=1)
                outcomes.append("updated")
            except ValueError:
                outcomes.append("conflict")
            except Exception as exc:  # surfaced by the assertion below
                outcomes.append(f"error:{type(exc).__name__}")

        first = Thread(target=update, args=(2,))
        second = Thread(target=update, args=(3,))
        first.start()
        second.start()
        barrier.wait()
        first.join(timeout=5)
        second.join(timeout=5)

        assert not first.is_alive()
        assert not second.is_alive()
        assert sorted(outcomes) == ["conflict", "updated"]
        assert db.get_resource(resource.id).revision == 2
    finally:
        db.close()


def test_memory_home_is_one_shared_database_across_threads():
    db = AIDB(":memory:")
    try:
        main_connection = db.db
        first = db.create_resource("item", {"index": 0})
        workers_count = 3
        barrier = Barrier(workers_count + 1)
        errors = []

        def work(index):
            barrier.wait()
            try:
                # The shared-connection path: every thread must see the
                # same single connection, hence the same database.
                assert db.db is main_connection
                db.create_resource("item", {"index": index + 1})
                assert db.get_resource(first.id).content == {"index": 0}
            except Exception as exc:  # surfaced by the assertion below
                errors.append(f"worker {index}: {type(exc).__name__}: {exc}")

        threads = [Thread(target=work, args=(i,)) for i in range(workers_count)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=5)

        assert all(not t.is_alive() for t in threads)
        assert errors == []
        assert len(db.list_resources()) == 1 + workers_count
    finally:
        db.close()


def test_close_from_another_thread_closes_every_connection(tmp_path):
    db = AIDB(tmp_path / "home.sqlite3")
    touched = Event()

    def touch():
        db.create_resource("item", {"value": 1})
        touched.set()

    worker = Thread(target=touch)
    worker.start()
    assert touched.wait(timeout=5)
    worker.join(timeout=5)

    # The worker's connection is registered on the store even though its
    # thread has exited; close() must shut it (and the main one) down.
    db.close()
    db.close()  # idempotent
    with pytest.raises(sqlite3.ProgrammingError):
        db.db.execute("SELECT 1")

    errors = []

    def use_after_close():
        try:
            db.list_resources()
        except sqlite3.ProgrammingError as exc:
            errors.append(exc)

    late = Thread(target=use_after_close)
    late.start()
    late.join(timeout=5)
    assert not late.is_alive()
    assert len(errors) == 1


def test_http_parallel_gets_and_posts_all_succeed(tmp_path):
    db = AIDB(tmp_path / "home.sqlite3")
    db.initialize_home(visibility="public")
    for i in range(5):
        db.create_resource("item", {"index": i}, visibility="public")
    server = create_server(db, port=0, auth_token="test-token")
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        barrier = Barrier(9)
        errors = []

        def get(path):
            barrier.wait()
            try:
                conn = HTTPConnection("127.0.0.1", server.server_port, timeout=10)
                conn.request("GET", path)
                response = conn.getresponse()
                body = response.read()
                assert response.status == 200, (path, response.status)
                if path == "/v1/resources":
                    assert len(json.loads(body)) == 5
                conn.close()
            except Exception as exc:  # surfaced by the assertion below
                errors.append(f"GET {path}: {type(exc).__name__}: {exc}")

        def post(index):
            barrier.wait()
            try:
                conn = HTTPConnection("127.0.0.1", server.server_port, timeout=10)
                conn.request(
                    "POST",
                    "/v1/notes",
                    body=json.dumps({"title": f"n{index}", "content": "x"}),
                    headers={
                        "Authorization": "Bearer test-token",
                        "Content-Type": "application/json",
                    },
                )
                response = conn.getresponse()
                response.read()
                assert response.status == 201, response.status
                conn.close()
            except Exception as exc:  # surfaced by the assertion below
                errors.append(f"POST {index}: {type(exc).__name__}: {exc}")

        threads = [
            Thread(target=get, args=("/v1/resources",)),
            Thread(target=get, args=("/v1/resources",)),
            Thread(target=get, args=("/v1/notes",)),
            Thread(target=get, args=("/specification",)),
            Thread(target=get, args=("/healthz",)),
            Thread(target=get, args=("/v1/changes",)),
            Thread(target=post, args=(0,)),
            Thread(target=post, args=(1,)),
        ]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=15)

        assert all(not t.is_alive() for t in threads)
        assert errors == []
        notes = db.db.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        assert notes == 2
    finally:
        server.shutdown()
        server.server_close()
        db.close()
