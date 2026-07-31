import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from db import execute, supabase
from utils.logger import logger

router = APIRouter(prefix='/api/auth', tags=['auth'])

TOKEN_TTL_DAYS = 30
_tokens: dict[str, str] = {}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_token(token: str) -> str:
    if not token:
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    username = _tokens.get(token)
    if username is not None:
        return username
    token_hash = _hash_token(token)
    result = execute(supabase.table('documents_tokens').select('data').eq('name', token_hash))
    if not result.data:
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    data = result.data[0]['data']
    if data.get('expires_at') and data['expires_at'] < _now_iso():
        execute(supabase.table('documents_tokens').delete().eq('name', token_hash))
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    username = data['username']
    _tokens[token] = username
    return username


def _prune_expired_tokens():
    try:
        execute(supabase.table('documents_tokens').delete().lt('data->>expires_at', _now_iso()))
    except Exception as e:
        logger.warning(f'Failed to prune expired tokens: {e}')


@router.post('/login')
def login(body: dict):
    try:
        username = body.get('username')
        password = body.get('password')

        if not username or not password:
            raise HTTPException(status_code=400, detail='username and password are required')

        result = execute(supabase.table('documents_userlist').select('data').eq('name', username))
        if not result.data:
            logger.warning('Login failed: user not found', extra={'username': username})
            raise HTTPException(status_code=401, detail='Invalid username or password')

        stored_password = result.data[0]['data'].get('password')
        if stored_password != password:
            logger.warning('Login failed: wrong password', extra={'username': username})
            raise HTTPException(status_code=401, detail='Invalid username or password')

        _prune_expired_tokens()

        token = secrets.token_hex(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS)).isoformat()
        execute(supabase.table('documents_tokens').upsert({
            'name': _hash_token(token),
            'data': {'username': username, 'expires_at': expires_at}
        }))
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
        if token:
            _tokens.pop(token, None)
            execute(supabase.table('documents_tokens').delete().eq('name', _hash_token(token)))
            logger.info('Logout successful')
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
