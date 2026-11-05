import threading

class SimpleConnectionPool:
    def __init__(self, minconn, maxconn, database=None):
        self.maxconn = maxconn
        self._semaphore = threading.Semaphore(maxconn)
        self._conn_count = 0

    def getconn(self):
        self._semaphore.acquire()
        self._conn_count += 1
        return {"id": f"db_conn_{id(self)}_{self._conn_count}", "status": "active"}

    def putconn(self, conn):
        if self._conn_count > 0:
            self._conn_count -= 1
            self._semaphore.release()