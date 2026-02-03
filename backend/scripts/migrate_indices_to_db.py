import json
import os
import sys
import logging

# Set PYTHONPATH
sys.path.append(os.getcwd())

from database import Base, sync_engine as engine, SessionLocal as Session
from models_alpha import IndexMaster, IndexConstituent, InstrumentMaster

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to the config file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'index_constituents.json')
# Adjustment if running from current directory or backend directory
if not os.path.exists(CONFIG_PATH):
    CONFIG_PATH = os.path.join('data', 'index_constituents.json')

def migrate_indices():
    """Migrate index data from JSON to Database."""
    logger.info(f"Loading index config from {CONFIG_PATH}")
    
    if not os.path.exists(CONFIG_PATH):
        logger.error("JSON config file not found!")
        return

    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

    # 1. Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    session = Session()

    try:
        # 2. Populate IndexMaster (First pass: names and descriptions)
        index_id_map = {} # name -> id
        
        # Sort indices to process base indices first if possible, 
        # but simpler is to process twice or use late resolution
        
        for name, data in config.items():
            if name.startswith('_'): continue
            
            # Check if exists
            existing = session.query(IndexMaster).filter_by(index_name=name).first()
            if not existing:
                idx = IndexMaster(
                    index_name=name,
                    description=data.get('description', '')
                )
                session.add(idx)
                session.flush() # Get ID
                index_id_map[name] = idx.index_id
                logger.info(f"Created IndexMaster entry: {name}")
            else:
                index_id_map[name] = existing.index_id
                logger.info(f"IndexMaster entry already exists: {name}")

        # 3. Second pass: base_index_id
        for name, data in config.items():
            if name.startswith('_'): continue
            base_name = data.get('base_index')
            if base_name and base_name in index_id_map:
                idx = session.query(IndexMaster).filter_by(index_name=name).one()
                idx.base_index_id = index_id_map[base_name]
                logger.info(f"Linked {name} to base index {base_name}")

        session.commit()

        # 4. Populate IndexConstituents
        # We need to resolve symbols to instrument_id
        for name, data in config.items():
            if name.startswith('_'): continue
            
            index_id = index_id_map[name]
            
            # Clear existing constituents to prevent duplicates during re-run
            # session.query(IndexConstituent).filter_by(index_id=index_id).delete()
            
            # We only add direct 'constituents' and 'additional_constituents'
            # (Recursive logic will be handled at query time or during explicit expansion)
            symbols = set(data.get('constituents', []))
            symbols.update(data.get('additional_constituents', []))
            
            if not symbols:
                continue
                
            logger.info(f"Processing {len(symbols)} symbols for {name}")
            
            added_count = 0
            for sym in symbols:
                # Find instrument_id
                instrument = session.query(InstrumentMaster).filter_by(symbol=sym).first()
                if instrument:
                    # Check if mapping already exists
                    mapping = session.query(IndexConstituent).filter_by(
                        index_id=index_id, 
                        instrument_id=instrument.instrument_id
                    ).first()
                    
                    if not mapping:
                        session.add(IndexConstituent(
                            index_id=index_id,
                            instrument_id=instrument.instrument_id
                        ))
                        added_count += 1
                else:
                    logger.warning(f"Symbol {sym} not found in instrument_master")
            
            session.commit()
            logger.info(f"Added {added_count} constituents to {name}")

        logger.info("Migration completed successfully!")

    except Exception as e:
        session.rollback()
        logger.error(f"Migration failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    migrate_indices()
