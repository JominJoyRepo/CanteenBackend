"""Manage authorized users in the documents_userlist table.

Usage:
    python manage_users.py list
    python manage_users.py add <username> <password>
    python manage_users.py remove <username>
"""
import sys

from db import supabase

TABLE = 'documents_userlist'


def list_users():
    result = supabase.table(TABLE).select('name', 'data').execute()
    for row in result.data:
        print(f'{row["name"]}: {row["data"]}')


def add_user(username: str, password: str):
    if not username or not password:
        print('ERROR: username and password are required')
        sys.exit(1)
    existing = supabase.table(TABLE).select('name').eq('name', username).execute()
    if existing.data:
        supabase.table(TABLE).update({'data': {'password': password}}).eq('name', username).execute()
        print(f'User "{username}" updated')
    else:
        supabase.table(TABLE).insert({'name': username, 'data': {'password': password}}).execute()
        print(f'User "{username}" added')


def remove_user(username: str):
    existing = supabase.table(TABLE).select('name').eq('name', username).execute()
    if not existing.data:
        print(f'User "{username}" not found')
        sys.exit(1)
    supabase.table(TABLE).delete().eq('name', username).execute()
    print(f'User "{username}" removed')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]
    if action == 'list':
        list_users()
    elif action == 'add' and len(sys.argv) == 4:
        add_user(sys.argv[2], sys.argv[3])
    elif action == 'remove' and len(sys.argv) == 3:
        remove_user(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)
