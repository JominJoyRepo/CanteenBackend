import secrets

from fastapi import APIRouter, HTTPException

from db import supabase
from utils.logger import logger

router = APIRouter(prefix='/api/auth', tags=['auth'])

_tokens: dict[str, str] = {}


def get_username_from_token(token: str):
    return _tokens.get(token)


def verify_token(token: str) -> str:
    username = _tokens.get(token)
    if username is None:
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    return username


@router.post('/login')
def login(body: dict):
    try:
        username = body.get('username')
        password = body.get('password')

        if not username or not password:
            raise HTTPException(status_code=400, detail='username and password are required')

        result = supabase.table('documents_userlist').select('data').eq('name', username).execute()
        if not result.data:
            logger.warning('Login failed: user not found', extra={'username': username})
            raise HTTPException(status_code=401, detail='Invalid username or password')

        stored_password = result.data[0]['data'].get('password')
        if stored_password != password:
            logger.warning('Login failed: wrong password', extra={'username': username})
            raise HTTPException(status_code=401, detail='Invalid username or password')

        token = secrets.token_hex(32)
        _tokens[token] = username
        logger.info('Login successful', extra={'username': username})
        return {'token': token, 'username': username}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to login: {e}')
        raise HTTPException(status_code=500, detail='Failed to login')


@router.post('/logout')
def logout(body: dict = None):
    try:
        token = (body or {}).get('token')
        if token and token in _tokens:
            username = _tokens.pop(token)
            logger.info('Logout successful', extra={'username': username})
        return {'success': True}
    except Exception as e:
        logger.error(f'Failed to logout: {e}')
        raise HTTPException(status_code=500, detail='Failed to logout')


@router.get('/me')
def me(token: str = None):
    try:
        if not token:
            raise HTTPException(status_code=401, detail='Token required')
        username = verify_token(token)
        return {'username': username}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to check session: {e}')
        raise HTTPException(status_code=500, detail='Failed to check session')
