from fastapi import APIRouter, HTTPException

from db import execute, supabase
from utils.logger import logger

router = APIRouter(prefix='/api/stores', tags=['stores'])


@router.get('')
def list_stores():
    try:
        result = execute(supabase.table('documents_stores').select('name', 'data'))
        return [{'id': row['name'], **row['data']} for row in result.data]
    except Exception as e:
        logger.error(f'Failed to list stores: {e}')
        raise HTTPException(status_code=500, detail='Failed to list stores')
