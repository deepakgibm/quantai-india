import clickhouse_connect
import logging
from config import settings

logger = logging.getLogger(__name__)

class ClickHouseClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ClickHouseClient, cls).__new__(cls)
            cls._instance.client = None
        return cls._instance

    def connect(self):
        """Establish connection to ClickHouse server."""
        if self.client is None:
            try:
                self.client = clickhouse_connect.get_client(
                    host=settings.CLICKHOUSE_HOST,
                    port=settings.CLICKHOUSE_PORT,
                    username=settings.CLICKHOUSE_USER,
                    password=settings.CLICKHOUSE_PASSWORD,
                    database=settings.CLICKHOUSE_DB
                )
                logger.info("Successfully connected to ClickHouse DB.")
            except Exception as e:
                logger.error(f"Failed to connect to ClickHouse: {e}")
                raise
        return self.client

    def query_as_dataframe(self, query: str, parameters: dict = None):
        """Query ClickHouse and return a Pandas DataFrame for vectorized indicators."""
        client = self.connect()
        try:
            # Use query_df to get pandas dataframe
            return client.query_df(query, parameters)
        except Exception as e:
            logger.error(f"ClickHouse query failed: {e}")
            raise

    def execute(self, query: str, parameters: dict = None):
        """Execute non-query command (like DDL or insert)."""
        client = self.connect()
        try:
            return client.command(query, parameters)
        except Exception as e:
            logger.error(f"ClickHouse execution failed: {e}")
            raise
            
    def insert(self, table: str, data: list, column_names: list = None):
        """Bulk insert rows into ClickHouse table."""
        client = self.connect()
        try:
            return client.insert(table, data, column_names=column_names)
        except Exception as e:
            logger.error(f"ClickHouse bulk insert failed: {e}")
            raise
