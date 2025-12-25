"""
Parquet Archive Service
Archives historical stock data to Parquet format for cold storage.
Reduces database size while maintaining query capability via DuckDB.
"""

import os
import pandas as pd
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger(__name__)

# Optional: Use pyarrow for better Parquet compression
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False
    logger.warning("PyArrow not available, using pandas Parquet writer")

from config import settings


class ParquetArchiveService:
    """
    Archives old stock data to Parquet files.
    
    Benefits:
    - 5-10x compression vs PostgreSQL
    - Fast analytical queries via DuckDB
    - Can be stored on cheap object storage (S3, GCS)
    - Reduces main database size
    """
    
    def __init__(self, archive_dir: str = None):
        """
        Initialize archive service.
        
        Args:
            archive_dir: Directory for Parquet files
        """
        self.archive_dir = archive_dir or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'parquet'
        )
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        
        # Ensure archive directory exists
        Path(self.archive_dir).mkdir(parents=True, exist_ok=True)
    
    def archive_month(self, year: int, month: int, 
                      delete_after: bool = False) -> Dict:
        """
        Archive one month of data to Parquet.
        
        Args:
            year: Year to archive (e.g., 2024)
            month: Month to archive (1-12)
            delete_after: If True, delete data from DB after successful archive
        
        Returns:
            Dict with archive statistics
        """
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        logger.info(f"Archiving data from {start_date} to {end_date}")
        
        session = self._Session()
        try:
            # Fetch data for the month
            query = text("""
                SELECT id, symbol, timestamp, open, high, low, close, volume, 
                       interval, source, created_at
                FROM stock_data
                WHERE timestamp >= :start_date AND timestamp < :end_date
                ORDER BY symbol, timestamp
            """)
            
            result = session.execute(query, {
                'start_date': start_date,
                'end_date': end_date
            })
            
            rows = result.fetchall()
            
            if not rows:
                logger.warning(f"No data found for {year}-{month:02d}")
                return {"status": "no_data", "rows": 0}
            
            # Convert to DataFrame
            columns = ['id', 'symbol', 'timestamp', 'open', 'high', 'low', 
                      'close', 'volume', 'interval', 'source', 'created_at']
            df = pd.DataFrame(rows, columns=columns)
            
            # Generate output filename
            filename = f"stock_data_{year}_{month:02d}.parquet"
            filepath = os.path.join(self.archive_dir, filename)
            
            # Write Parquet file
            if PYARROW_AVAILABLE:
                # Use PyArrow for better compression
                table = pa.Table.from_pandas(df)
                pq.write_table(
                    table, 
                    filepath,
                    compression='zstd',
                    compression_level=3
                )
            else:
                # Fallback to pandas
                df.to_parquet(filepath, compression='gzip', index=False)
            
            # Get file size
            file_size = os.path.getsize(filepath)
            
            stats = {
                "status": "success",
                "year": year,
                "month": month,
                "rows_archived": len(df),
                "symbols": df['symbol'].nunique(),
                "file_path": filepath,
                "file_size_mb": round(file_size / (1024 * 1024), 2)
            }
            
            logger.info(f"Archived {len(df)} rows to {filepath} ({stats['file_size_mb']} MB)")
            
            # Optionally delete from database
            if delete_after:
                delete_query = text("""
                    DELETE FROM stock_data
                    WHERE timestamp >= :start_date AND timestamp < :end_date
                """)
                result = session.execute(delete_query, {
                    'start_date': start_date,
                    'end_date': end_date
                })
                session.commit()
                stats["rows_deleted"] = result.rowcount
                logger.info(f"Deleted {result.rowcount} rows from database")
            
            return stats
            
        except Exception as e:
            logger.error(f"Archive failed: {e}")
            session.rollback()
            return {"status": "error", "error": str(e)}
        finally:
            session.close()
    
    def archive_old_data(self, months_to_keep: int = 12, 
                         delete_after: bool = False) -> List[Dict]:
        """
        Archive all data older than specified months.
        
        Args:
            months_to_keep: Keep this many months in the database
            delete_after: If True, delete archived data from DB
        
        Returns:
            List of archive results per month
        """
        cutoff_date = datetime.now() - timedelta(days=months_to_keep * 30)
        
        # Get distinct year-months to archive
        session = self._Session()
        try:
            query = text("""
                SELECT DISTINCT 
                    EXTRACT(YEAR FROM timestamp)::int as year,
                    EXTRACT(MONTH FROM timestamp)::int as month
                FROM stock_data
                WHERE timestamp < :cutoff_date
                ORDER BY year, month
            """)
            
            result = session.execute(query, {'cutoff_date': cutoff_date})
            months_to_archive = result.fetchall()
            
            results = []
            for year, month in months_to_archive:
                result = self.archive_month(year, month, delete_after=delete_after)
                results.append(result)
            
            return results
            
        finally:
            session.close()
    
    def restore_from_archive(self, year: int, month: int) -> Dict:
        """
        Restore archived data back to database.
        
        Args:
            year: Year to restore
            month: Month to restore
        
        Returns:
            Dict with restore statistics
        """
        filename = f"stock_data_{year}_{month:02d}.parquet"
        filepath = os.path.join(self.archive_dir, filename)
        
        if not os.path.exists(filepath):
            return {"status": "error", "error": f"Archive file not found: {filepath}"}
        
        try:
            # Read Parquet file
            df = pd.read_parquet(filepath)
            
            # Insert into database (in batches)
            session = self._Session()
            batch_size = 10000
            total_inserted = 0
            
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                
                # Use pandas to_sql for simplicity
                batch.to_sql(
                    'stock_data', 
                    self._engine, 
                    if_exists='append', 
                    index=False,
                    method='multi'
                )
                total_inserted += len(batch)
                logger.info(f"Inserted batch {i//batch_size + 1}: {total_inserted}/{len(df)}")
            
            return {
                "status": "success",
                "year": year,
                "month": month,
                "rows_restored": total_inserted
            }
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def list_archives(self) -> List[Dict]:
        """List all available archive files."""
        archives = []
        
        for pq_file in Path(self.archive_dir).glob("*.parquet"):
            try:
                df = pd.read_parquet(pq_file, columns=['symbol'])
                archives.append({
                    "filename": pq_file.name,
                    "path": str(pq_file),
                    "size_mb": round(pq_file.stat().st_size / (1024 * 1024), 2),
                    "rows": len(df),
                    "symbols": df['symbol'].nunique()
                })
            except Exception as e:
                archives.append({
                    "filename": pq_file.name,
                    "path": str(pq_file),
                    "error": str(e)
                })
        
        return archives
    
    def get_archive_stats(self) -> Dict:
        """Get overall archive statistics."""
        archives = self.list_archives()
        
        return {
            "archive_dir": self.archive_dir,
            "total_files": len(archives),
            "total_size_mb": sum(a.get('size_mb', 0) for a in archives),
            "total_rows": sum(a.get('rows', 0) for a in archives),
            "archives": archives
        }


# Singleton instance
_archive_service: Optional[ParquetArchiveService] = None


def get_archive_service() -> ParquetArchiveService:
    """Get singleton archive service instance."""
    global _archive_service
    if _archive_service is None:
        _archive_service = ParquetArchiveService()
    return _archive_service


# CLI interface
if __name__ == "__main__":
    import sys
    
    service = get_archive_service()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python parquet_archive.py list          - List archives")
        print("  python parquet_archive.py stats         - Show statistics")
        print("  python parquet_archive.py archive 2024 10 - Archive Oct 2024")
        print("  python parquet_archive.py archive-old 12 - Archive data older than 12 months")
        print("  python parquet_archive.py restore 2024 10 - Restore Oct 2024")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "list":
        for archive in service.list_archives():
            print(archive)
    
    elif command == "stats":
        print(service.get_archive_stats())
    
    elif command == "archive" and len(sys.argv) >= 4:
        year = int(sys.argv[2])
        month = int(sys.argv[3])
        delete = "--delete" in sys.argv
        result = service.archive_month(year, month, delete_after=delete)
        print(result)
    
    elif command == "archive-old" and len(sys.argv) >= 3:
        months = int(sys.argv[2])
        delete = "--delete" in sys.argv
        results = service.archive_old_data(months_to_keep=months, delete_after=delete)
        for r in results:
            print(r)
    
    elif command == "restore" and len(sys.argv) >= 4:
        year = int(sys.argv[2])
        month = int(sys.argv[3])
        result = service.restore_from_archive(year, month)
        print(result)
    
    else:
        print(f"Unknown command: {command}")
