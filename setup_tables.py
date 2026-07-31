"""
Setup script for Supabase tables.

Before running this script, create the tables in your Supabase SQL editor:

    CREATE TABLE IF NOT EXISTS documents_stores (
        name TEXT PRIMARY KEY,
        data JSONB NOT NULL
    );

    CREATE TABLE IF NOT EXISTS documents_store1 (
        name TEXT PRIMARY KEY,
        data JSONB NOT NULL
    );

    CREATE TABLE IF NOT EXISTS documents_store2 (
        name TEXT PRIMARY KEY,
        data JSONB NOT NULL
    );

    CREATE TABLE IF NOT EXISTS documents_userlist (
        name TEXT PRIMARY KEY,
        data JSONB NOT NULL
    );

    ALTER TABLE documents_store1 ADD COLUMN IF NOT EXISTS "user" TEXT;
    ALTER TABLE documents_store2 ADD COLUMN IF NOT EXISTS "user" TEXT;

After creating tables, run this script to seed data from local JSON files.
"""
import json
from pathlib import Path

from db import supabase

DATA_DIR = Path(__file__).resolve().parent / 'data'

TABLES = ['documents_stores', 'documents_store1', 'documents_store2', 'documents_userlist']


def tables_exist() -> bool:
    for table in TABLES:
        try:
            supabase.table(table).select('name').limit(1).execute()
        except Exception:
            return False
    return True


def seed_stores():
    for entry in sorted(DATA_DIR.iterdir()):
        if entry.is_dir():
            store_file = entry / 'store.json'
            if store_file.exists():
                with open(store_file, 'r', encoding='utf-8') as f:
                    store_data = json.load(f)
                name = store_data['id']
                existing = supabase.table('documents_stores').select('name').eq('name', name).execute()
                if existing.data:
                    print(f'Store "{name}" already exists, skipping')
                    continue
                supabase.table('documents_stores').insert({'name': name, 'data': {'name': store_data['name']}}).execute()
                print(f'Seeded store "{name}"')


def seed_templates():
    for entry in sorted(DATA_DIR.iterdir()):
        if entry.is_dir():
            store_id = entry.name
            table = f"documents_{store_id.replace('-', '')}"
            template_file = entry / 'template.json'
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                existing = supabase.table(table).select('name').eq('name', 'template').execute()
                if existing.data:
                    print(f'Template for "{store_id}" already exists, skipping')
                    continue
                supabase.table(table).insert({'name': 'template', 'data': template_data}).execute()
                print(f'Seeded template for "{store_id}"')


def seed_records():
    for entry in sorted(DATA_DIR.iterdir()):
        if entry.is_dir():
            store_id = entry.name
            table = f"documents_{store_id.replace('-', '')}"
            records_dir = entry / 'records'
            if not records_dir.exists():
                continue
            for record_file in sorted(records_dir.iterdir()):
                if record_file.suffix == '.json':
                    date_str = record_file.stem
                    with open(record_file, 'r', encoding='utf-8') as f:
                        record_data = json.load(f)
                    existing = supabase.table(table).select('name').eq('name', date_str).execute()
                    if existing.data:
                        print(f'Record "{date_str}" for "{store_id}" already exists, skipping')
                        continue
                    supabase.table(table).insert({'name': date_str, 'data': record_data}).execute()
                    print(f'Seeded record "{date_str}" for "{store_id}"')


def seed_users():
    default_users = [
        {'name': 'admin', 'data': {'password': 'admin123'}},
    ]
    for user in default_users:
        existing = supabase.table('documents_userlist').select('name').eq('name', user['name']).execute()
        if existing.data:
            print(f'User "{user["name"]}" already exists, skipping')
            continue
        supabase.table('documents_userlist').insert(user).execute()
        print(f'Seeded user "{user["name"]}"')


if __name__ == '__main__':
    if not tables_exist():
        print('ERROR: Tables do not exist.')
        print('Please create them first via Supabase SQL Editor using the SQL at the top of this file.')
        exit(1)
    seed_stores()
    seed_templates()
    seed_records()
    seed_users()
    print('Done!')
