import oracledb

class OracleDB:
    _connections = {}
    _databases = {}

    @classmethod
    def config_database(cls, db_name, db_config):
        """
        db_config = {
            "user": "...",
            "password": "...",
            "dsn": "...",
            "encoding": "AL32UTF8"
        }
        """
        cls._databases[db_name] = db_config

    @classmethod
    def connect(cls, db_name):
        if db_name not in cls._databases:
            raise ValueError(f"Database config '{db_name}' not found")

        db_conf = cls._databases[db_name]
        conn = oracledb.connect(
            user=db_conf["USER"],
            password=db_conf["PASSWORD"],
            dsn=db_conf["NAME"]
            # encoding=db_conf.get("encoding", "AL32UTF8")
        )
        cls._connections[db_name] = conn
        return conn

    @classmethod
    def get_connection(cls, db_name):
        if db_name not in cls._connections:
            return cls.connect(db_name)
        try:
            cls._connections[db_name].ping()
        except oracledb.DatabaseError:
            return cls.connect(db_name)
        return cls._connections[db_name]

    @classmethod
    def connection(cls, db_name):
        """
        Return a context-manageable connection object.
        """
        conn = cls.get_connection(db_name)
        return _OracleConnectionContext(conn)


class _OracleConnectionContext:
    """
    Wraps a cx_Oracle/oracledb Connection so it works as a context manager.
    """
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()

        # Closing the connection so it can be per connection base
        self.conn.close()