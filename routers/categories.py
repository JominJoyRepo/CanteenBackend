from fastapi import APIRouter, HTTPException, Query

from db import supabase
from utils.logger import logger

router = APIRouter(prefix='/api/categories', tags=['categories'])


def store_table(store_id: str) -> str:
    return f"documents_{store_id.replace('-', '')}"


def load_template(store_id: str):
    table = store_table(store_id)
    result = supabase.table(table).select('data').eq('name', 'template').execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f'Store "{store_id}" not found')
    return result.data[0]['data']


@router.get('')
def list_categories(storeId: str = Query(...)):
    try:
        data = load_template(storeId)
        return [{'id': c['id'], 'name': c['name']} for c in data['categories']]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to load categories (storeId={storeId}): {e}')
        raise HTTPException(status_code=500, detail='Failed to load categories')


@router.get('/{category_id}/items')
def get_category_items(category_id: str, storeId: str = Query(...)):
    try:
        data = load_template(storeId)
        category = next((c for c in data['categories'] if c['id'] == category_id), None)
        if not category:
            logger.warning('Category not found', extra={'categoryId': category_id, 'storeId': storeId})
            raise HTTPException(status_code=404, detail='Category not found')
        return category['items']
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to load items (categoryId={category_id}, storeId={storeId}): {e}')
        raise HTTPException(status_code=500, detail='Failed to load items')


@router.get('/with-prices')
def list_categories_with_prices(storeId: str = Query(...)):
    try:
        data = load_template(storeId)
        result = []
        for cat in data['categories']:
            items = [{'id': i['id'], 'name': i['name'], 'unit': i['unit'], 'price': i.get('price')} for i in cat['items']]
            result.append({'id': cat['id'], 'name': cat['name'], 'items': items})
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to load categories with prices (storeId={storeId}): {e}')
        raise HTTPException(status_code=500, detail='Failed to load categories with prices')


@router.put('/{category_id}/items/{item_id}/price')
def update_item_price(category_id: str, item_id: str, body: dict):
    try:
        store_id = body.get('storeId')
        new_price = body.get('price')

        if store_id is None or new_price is None:
            raise HTTPException(status_code=400, detail='storeId and price are required')

        template = load_template(store_id)
        category = next((c for c in template['categories'] if c['id'] == category_id), None)
        if not category:
            raise HTTPException(status_code=404, detail='Category not found')

        item = next((i for i in category['items'] if i['id'] == item_id), None)
        if not item:
            raise HTTPException(status_code=404, detail='Item not found')

        item['price'] = new_price
        table = store_table(store_id)
        supabase.table(table).upsert({'name': 'template', 'data': template}).execute()

        logger.info('Item price updated', extra={'storeId': store_id, 'categoryId': category_id, 'itemId': item_id, 'price': new_price})
        return {'success': True, 'item': item}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to update item price (itemId={item_id}): {e}')
        raise HTTPException(status_code=500, detail='Failed to update item price')
