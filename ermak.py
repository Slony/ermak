"""Executable module with main working horse class definition."""


from datetime import date
from datetime import datetime
from datetime import timedelta
import logging
import sys
import time
import warnings
from config import ARGS
from config import CFG
import db
import ga


class Ermak(object):
  """Ermak's main class with high-level workflow methods."""

  def __init__(self, cfg):
    self.cfg = cfg
    self.dbc = db.Client(cfg['db'])
    self.gac = ga.Client(cfg['ga'])
    self.hit_ids = []

  def bootstrap(self):
    """Sets Ermak database up and ready."""
    if 'bootstrap' not in self.cfg:
      logging.warn('No bootstrap section in config, bootstrapping skipped')
      return
    with warnings.catch_warnings():
      warnings.simplefilter('ignore')
      for sql in self.cfg['bootstrap']:
        self.dbc.run(sql)

  def extract(self):
    """Updates report tables with fresh data from GA."""
    if 'extract' not in self.cfg:
      logging.warn('No extract section in config, extraction skipped')
      return
    one_day = timedelta(1)
    today = date.today() - 2 * one_day
    for report in self.cfg['extract']:
      logging.info('update %s', report['table'])
      dimensions = report['dimensions']
      metrics = report['metrics']
      keys = dimensions + metrics
      try:
        filters = report['filters']
      except KeyError:
        filters = None
      self.dbc.run('SELECT ADDDATE(MAX(DATE(%s)), 1) FROM %s' %
                   (report['datetime_field'], report['table']))
      day_str = self.dbc.one()[0]
      if not day_str:
        day_str = self.cfg['big_bang']
      day = datetime.strptime(day_str, '%Y-%m-%d').date()
      while day < today:
        day_str = day.strftime('%Y-%m-%d')
        logging.info('  fetch data for %s', day_str)
        rows = self.gac.get_rows(day_str, dimensions, metrics, filters)
        if rows:
          values = []
          for row in rows:
            row_escaped = [self.dbc.esc(c) for c in row]
            row_dict = dict(zip(keys, row_escaped))
            row_dict['date'] = day_str
            values.append(report['values'] % row_dict)
          self.dbc.run('INSERT IGNORE %s VALUES (%s)' %
                       (report['table'], '),\n('.join(values)))
        day += one_day

  def process(self):
    """Processes data collected in DB."""
    if 'process' not in self.cfg:
      logging.warn('No process section in config, processing skipped')
      return
    for query in self.cfg['process']:
      logging.info(query['title'])
      self.dbc.run(query['sql'])
    self.dbc.fix()

  def send(self):
    """Sends data processing results to dedicated GA account."""
    if 'send' not in self.cfg:
      logging.warn('No send section in config, hits sending skipped')
      return
    logging.info('send hits')
    self.dbc.run(self.cfg['send']['sql'])
    keys = self.dbc.fields()
    until = {}
    for row in self.dbc.all():
      hit = dict(zip(keys, row))
      if hit['is_new_session']:
        if hit['wait_key'] in until:
          wait = until[hit['wait_key']] - self._now()
          if wait > 0:
            logging.info('  sleep for %i second(s)', wait)
            time.sleep(wait)
      ga.send({k: hit[k] for k in keys
               if k not in ('hit_id', 'is_new_session', 'wait_key')})
      self._submit(hit['hit_id'])
      until[hit['wait_key']] = self._now() + 90
    self._flush()

  def _submit(self, hit_id):
    """Appends a hit ID to the buffer and flushes it once per 100 hits."""
    self.hit_ids.append(hit_id)
    if len(self.hit_ids) == 100:
      self._flush()

  def _flush(self):
    """Updates hits table and marks hits with buffered IDs as already sent."""
    if self.hit_ids:
      if isinstance(self.hit_ids[0], str):
        s, q = "','", "'"
      else:
        s, q = ',', ''
      hit_ids = q + s.join([str(i) for i in self.hit_ids]) + q
      cur = self.dbc.db.cursor()
      sql = self.cfg['send']['flush'] % hit_ids
      self.dbc.run(sql, cur=cur)
      cur.close()
      self.hit_ids = []

  def _now(self):
    """Returns current time as seconds since Unix epoch."""
    return int(time.time())


def main():
  # Teaching Python to understand UTF-8:
  reload(sys)
  sys.setdefaultencoding('utf8')

  ermak = Ermak(CFG)
  if not ARGS.skip_bootstrapping:
    ermak.bootstrap()
  if not ARGS.skip_extraction:
    ermak.extract()
  if not ARGS.skip_processing:
    ermak.process()
  if not ARGS.skip_sending:
    ermak.send()


if __name__ == '__main__':
  main()

