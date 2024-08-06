# license.py
import logging
from datetime import datetime, timedelta
import aiosqlite
import secrets
from config import DB_NAME

logger = logging.getLogger(__name__)

async def is_valid_license(key):
    logger.debug(f"Checking license key: {key}")
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM licenses WHERE key = ?", (key,)) as cursor:
            license = await cursor.fetchone()
            
    if not license:
        logger.warning(f"License key not found: {key}")
        return False
    
    if license[2] == 'subscription':
        is_valid = datetime.now() < datetime.fromisoformat(license[3])
        logger.debug(f"Subscription license valid: {is_valid}")
        return is_valid
    
    logger.debug("One-time license, always valid")
    return True

async def create_license(key, license_type, expiration=None):
    if not key:
        key = secrets.token_urlsafe(16)  # Generate a secure random key if not provided
    
    if license_type == 'subscription' and not expiration:
        expiration = (datetime.now() + timedelta(days=30)).isoformat()
    
    logger.debug(f"Creating license: key={key}, type={license_type}, expiration={expiration}")
    
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("INSERT INTO licenses (key, type, expiration) VALUES (?, ?, ?)",
                             (key, license_type, expiration))
            await db.commit()
        logger.info(f"License created successfully: {key}")
        return key
    except aiosqlite.IntegrityError:
        logger.warning(f"Attempt to create duplicate license key: {key}")
        return None
    except Exception as e:
        logger.error(f"Error creating license: {str(e)}")
        return None

async def revoke_license(key):
    logger.debug(f"Revoking license: {key}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM licenses WHERE key = ?", (key,))
        changes = db.total_changes
        await db.commit()
    
    if changes:
        logger.info(f"License revoked successfully: {key}")
        return True
    else:
        logger.warning(f"License not found for revocation: {key}")
        return False

async def update_license_expiration(key, new_expiration):
    logger.debug(f"Updating license expiration: key={key}, new_expiration={new_expiration}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE licenses SET expiration = ? WHERE key = ?", (new_expiration, key))
        changes = db.total_changes
        await db.commit()
    
    if changes:
        logger.info(f"License expiration updated successfully: {key}")
        return True
    else:
        logger.warning(f"License not found for update: {key}")
        return False