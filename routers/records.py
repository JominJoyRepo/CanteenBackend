from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Header, Query

from db import execute, supabase
from routers.auth import verify_token
from utils.logger import logger

router = APIRouter(prefix='/api/records', tags=['records'])

DEFAULT_CATEGORY_ID = 'other'
DEFAULT_CATEGORY_NAME = 'Other Items'


def get_username_from_auth(authorization: str) -> str:
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing or invalid Authorization header')
    return verify_token(authorization[len('Bearer '):])


def store_table(store_id: str) -> str:
    return f"documents_{store_id.replace('-', '')}"


def load_template(store_id: str):
    table = store_table(store_id)
    result = execute(supabase.table(table).select('data').eq('name', 'template'))
    if not result.data:
        raise HTTPException(status_code=404, detail=f'Store "{store_id}" not found')
    return result.data[0]['data']


def get_date_str(dt: datetime = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime('%Y-%m-%d')


def load_records(store_id: str, date_str: str):
    table = store_table(store_id)
    result = execute(supabase.table(table).select('data', '"user"').eq('name', date_str))
    if not result.data:
        return None
    records = result.data[0]['data']
    records['user'] = result.data[0].get('user')
    return records


def save_records(store_id: str, date_str: str, data: dict, username: str = None):
    table = store_table(store_id)
    payload = {'name': date_str, 'data': data}
    if username:
        payload['user'] = username
    execute(supabase.table(table).upsert(payload))


def normalize_items(items: list) -> list:
    for item in items:
        if item.get('openStock') is None:
            item['openStock'] = 0
        if item.get('closedStock') is None:
            item['closedStock'] = 0
    return items


@router.get('')
def get_records(storeId: str = Query(...), date: str = Query(None)):
    try:
        date_str = date if date else get_date_str()
        records = load_records(storeId, date_str)
        if records is None:
            return {'date': date_str, 'storeId': storeId, 'entries': []}
        return {**records, 'storeId': storeId}
    except Exception as e:
        logger.error(f'Failed to load records (storeId={storeId}, date={date}): {e}')
        raise HTTPException(status_code=500, detail='Failed to load records')


@router.post('')
def create_record(body: dict, authorization: str = Header(None)):
    try:
        username = get_username_from_auth(authorization)
        store_id = body.get('storeId')
        category_id = body.get('categoryId')
        items = body.get('items')

        if not store_id or not category_id or items is None:
            logger.warning('Missing required fields', extra={'storeId': store_id, 'categoryId': category_id, 'items': items})
            raise HTTPException(status_code=400, detail='storeId, categoryId, and items are required')

        if category_id == DEFAULT_CATEGORY_ID:
            category_name = DEFAULT_CATEGORY_NAME
        else:
            template = load_template(store_id)
            category = next((c for c in template['categories'] if c['id'] == category_id), None)
            if not category:
                logger.warning('Invalid category', extra={'storeId': store_id, 'categoryId': category_id})
                raise HTTPException(status_code=400, detail='Invalid category')
            category_name = category['name']

        date_str = body.get('date') or get_date_str()

        records = load_records(store_id, date_str)
        if records is None:
            records = {'date': date_str, 'storeId': store_id, 'entries': []}

        existing_idx = next(
            (i for i, e in enumerate(records['entries']) if e['categoryId'] == category_id),
            None
        )
        entry = {'categoryId': category_id, 'categoryName': category_name, 'items': normalize_items(items)}

        if existing_idx is not None:
            records['entries'][existing_idx] = entry
        else:
            records['entries'].append(entry)

        save_records(store_id, date_str, records, username)
        logger.info('Record saved', extra={'storeId': store_id, 'date': date_str, 'categoryId': category_id, 'user': username})
        return {'success': True, 'date': date_str, 'storeId': store_id, 'entry': entry}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to save record: {e}')
        raise HTTPException(status_code=500, detail='Failed to save record')


@router.put('/{date}')
def update_record(date: str, body: dict, authorization: str = Header(None)):
    try:
        username = get_username_from_auth(authorization)
        store_id = body.get('storeId')
        category_id = body.get('categoryId')
        items = body.get('items')

        if not store_id or not category_id or items is None:
            logger.warning('Missing required fields', extra={'storeId': store_id, 'categoryId': category_id, 'items': items, 'date': date})
            raise HTTPException(status_code=400, detail='storeId, categoryId, and items are required')

        records = load_records(store_id, date)
        if records is None:
            logger.warning('No records found', extra={'storeId': store_id, 'date': date})
            raise HTTPException(status_code=404, detail='No records found for this date')

        existing_idx = next(
            (i for i, e in enumerate(records['entries']) if e['categoryId'] == category_id),
            None
        )
        if existing_idx is None:
            logger.warning('Category entry not found', extra={'storeId': store_id, 'date': date, 'categoryId': category_id})
            raise HTTPException(status_code=404, detail='Category entry not found for this date')

        records['entries'][existing_idx]['items'] = normalize_items(items)
        save_records(store_id, date, records, username)
        logger.info('Record updated', extra={'storeId': store_id, 'date': date, 'categoryId': category_id, 'user': username})
        return {'success': True, 'date': date, 'storeId': store_id, 'entry': records['entries'][existing_idx]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to update record ({date}): {e}')
        raise HTTPException(status_code=500, detail='Failed to update record')


@router.put('/{date}/day')
def save_day_record(date: str, body: dict, authorization: str = Header(None)):
    try:
        username = get_username_from_auth(authorization)
        store_id = body.get('storeId')
        entries = body.get('entries')

        if not store_id or not isinstance(entries, list):
            logger.warning('Missing required fields', extra={'storeId': store_id, 'entriesType': type(entries).__name__})
            raise HTTPException(status_code=400, detail='storeId and entries are required')

        records = load_records(store_id, date)
        if records is None:
            records = {'date': date, 'storeId': store_id, 'entries': []}

        existing_summary = records.get('summary')
        for entry in entries:
            entry['items'] = normalize_items(entry.get('items') or [])
        records['entries'] = entries
        if existing_summary is not None:
            records['summary'] = existing_summary

        save_records(store_id, date, records, username)
        logger.info('Day record saved', extra={'storeId': store_id, 'date': date, 'user': username, 'categories': len(entries)})
        return {'success': True, 'date': date, 'storeId': store_id, 'entries': entries}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to save day record ({date}): {e}')
        raise HTTPException(status_code=500, detail='Failed to save day record')


@router.put('/{date}/summary')
def save_summary(date: str, body: dict, authorization: str = Header(None)):
    try:
        username = get_username_from_auth(authorization)
        store_id = body.get('storeId')
        cash_in = body.get('cashIn')
        cash_out = body.get('cashOut')
        card_sale = body.get('cardSale')
        diff = body.get('diff')

        if not store_id:
            raise HTTPException(status_code=400, detail='storeId is required')

        records = load_records(store_id, date)
        if records is None:
            records = {'date': date, 'storeId': store_id, 'entries': []}

        records['summary'] = {
            'cashIn': cash_in,
            'cashOut': cash_out,
            'cardSale': card_sale,
            'diff': diff
        }

        save_records(store_id, date, records, username)
        logger.info('Summary saved', extra={'storeId': store_id, 'date': date, 'user': username})
        return {'success': True, 'date': date, 'storeId': store_id, 'summary': records['summary']}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to save summary ({date}): {e}')
        raise HTTPException(status_code=500, detail='Failed to save summary')


@router.get('/dates')
def list_dates(storeId: str = Query(...)):
    try:
        table = store_table(storeId)
        result = execute(supabase.table(table).select('name'))
        dates = sorted(
            [row['name'] for row in result.data if row['name'] not in ('template', 'store')],
            reverse=True
        )
        return dates
    except Exception as e:
        logger.error(f'Failed to list dates (storeId={storeId}): {e}')
        raise HTTPException(status_code=500, detail='Failed to list dates')


@router.get('/previous')
def get_previous_record(storeId: str = Query(...), date: str = Query(...)):
    try:
        table = store_table(storeId)
        result = execute(supabase.table(table).select('name'))
        dates = sorted(
            [row['name'] for row in result.data if row['name'] not in ('template', 'store') and row['name'] < date]
        )
        if not dates:
            return None
        return load_records(storeId, dates[-1])
    except Exception as e:
        logger.error(f'Failed to load previous record (storeId={storeId}, date={date}): {e}')
        raise HTTPException(status_code=500, detail='Failed to load previous record')
