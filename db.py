"""Module with MySql client class."""


import logging
import MySQLdb


class Client(object):
  """Ermak's MySql client class made for convenience."""

  def __init__(self, cfg):
    """Inits client instance and sets utf-8 encoding."""
    self.prefix = cfg['prefix']
    connection_cfg = {k: cfg[k] for k in ('host', 'user', 'passwd', 'db')}
    self.db = MySQLdb.connect(**connection_cfg)
    self.db.autocommit(True)
    self.db.set_character_set('utf8')
    self.cur = self.db.cursor()
    self.run('SET NAMES utf8')
    self.run('SET CHARACTER SET utf8')
    self.run('SET character_set_connection=utf8')

  def __del__(self):
    """Closes DB cursor and connection on client's destroy."""
    self.cur.close()
    self.db.close()

  def run(self, sql, cur=None):
    """Executes SQL query.

    Args:
      sql: SQL query as a string.
      cur: DB cursor if in need to execute query with separate cursor.
    """
    prefixed_sql = sql.replace('^', self.prefix)
    logging.debug(prefixed_sql)
    if cur is None:
      self.cur.execute(prefixed_sql)
    else:
      cur.execute(prefixed_sql)

  def fields(self):
    """Returns list of result field names.

    Returns:
      A list of strings with result field names.
    """
    return [f[0] for f in self.cur.description]

  def one(self):
    """Returns the next single row of data fetched from DB.

    Returns:
      A tuple with row values.
    """
    return self.cur.fetchone()

  def all(self):
    """Returns all [remaining] rows of data fetched from DB.

    Returns:
      A list of tuples with rows' values.
    """
    return self.cur.fetchall()

  def fix(self):
    """Purges data fetched from DB to get cursor ready for the next query."""
    self.cur.close()
    self.cur = self.db.cursor()

  def esc(self, value):
    """Makes string value SQL-safe escaping quotes and backslashes.

    Args:
      value: string value to be scaped.

    Returns:
      An SQL-safe escaped string value.
    """
    return value.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"')


def main():
  pass


if __name__ == '__main__':
  main()

