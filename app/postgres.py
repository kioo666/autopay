"""Minimal DB-API adapter for the existing SQLite statements."""
import sqlite3
class Row(dict):
    def __getitem__(self,key):
        return tuple(self.values())[key] if isinstance(key,int) else super().__getitem__(key)
class Cursor:
    def __init__(self,cursor):self.cursor=cursor
    def fetchone(self):
        r=self.cursor.fetchone();return Row(r) if r is not None else None
    def fetchall(self):return [Row(r) for r in self.cursor.fetchall()]
    def __iter__(self):return (Row(r) for r in self.cursor)
def sql(statement):
    special={
      'INSERT OR REPLACE INTO secrets VALUES (?,?)':'INSERT INTO secrets (id,value) VALUES (%s,%s) ON CONFLICT (id) DO UPDATE SET value=EXCLUDED.value',
      'INSERT OR REPLACE INTO applications VALUES (?,?)':'INSERT INTO applications (id,config) VALUES (%s,%s) ON CONFLICT (id) DO UPDATE SET config=EXCLUDED.config'}
    return special.get(statement,statement.replace('?','%s')).replace(' BLOB',' BYTEA')
class Connection:
    def __init__(self,connection):self.connection=connection
    def execute(self,statement,params=None):
        import psycopg
        try:return Cursor(self.connection.execute(sql(statement),params))
        except psycopg.IntegrityError:raise sqlite3.IntegrityError('Constraint conflict') from None
    def executescript(self,script):
        for statement in script.split(';'):
            if statement.strip():self.execute(statement)
