"""Module with Google Analytics client class."""


import logging
import os
import time
from apiclient.discovery import build
from config import ARGS
from config import CFG
import googleapiclient.errors
import httplib2
from oauth2client.client import SignedJwtAssertionCredentials
import urlfetch


_GA_SCOPE = 'https://www.googleapis.com/auth/analytics.readonly'
_CLIENT_EMAIL = CFG['ga']['email']
if CFG['ga']['key_file'][0] == '/':
  _KEY_FILE = CFG['ga']['key_file']
else:
  _KEY_FILE = os.path.join(os.path.dirname(__file__), CFG['ga']['key_file'])


class Client(object):
  """Ermak's client used to access Analytics core reporting API."""

  def __init__(self, cfg):
    """Creates Ermak's Analytics core reporting API client."""
    self.view_id = cfg['view_id']
    with open(_KEY_FILE, 'rb') as key_file:
      self._private_key = key_file.read()
    self._authenticate()

  def _authenticate(self):
    """Authenticates Ermak's Analytics client and stores discovered service."""
    credentials = SignedJwtAssertionCredentials(
        _CLIENT_EMAIL,
        self._private_key,
        _GA_SCOPE
    )
    http = credentials.authorize(httplib2.Http())
    self._service = build('analytics', 'v3', http=http)

  def get(self, **kwargs):
    """Queries Analytics core reporting API and returns the result.

    Args:
      **kwargs: query parameters as described here:
          https://developers.google.com/analytics/devguides/reporting/core/v3

    Returns:
      A dict representation of received JSON object.
    """
    attempts_count = 0
    while attempts_count < 5:
      try:
        time.sleep(attempts_count * 5)
        return self._service.data().ga().get(**kwargs).execute()
      except googleapiclient.errors.HttpError:
        attempts_count += 1
    raise googleapiclient.errors.HttpError

  def get_rows(self, day, dimensions_list, metrics_list, filters):
    """Fetches dimensions data from GA for a given date.

    Args:
      day: A string representing date (e.g. '2016-07-17') to fetch data for.
      dimensions_list: A list of GA dimension names as strings
          (e.g. ['ga:adGroup', 'ga:keyword', 'ga:dimension5']).
      metrics_list: A list of GA metric names as strings (e.g. ['ga:sessions']).
      filters: A string with data filters as specified in Query Explorer (e.g.
          'ga:eventCategory==Purchases;ga:eventAction==First Purchase') or None
          if no filters have to be applied.

    Returns:
      A list of lists of strings with fetched data values.
    """
    dimensions = ','.join(dimensions_list)
    metrics = ','.join(metrics_list)
    all_rows = []
    start_index = 1
    max_results = 10000
    while True:
      result = self.get(
          ids=self.view_id,
          start_date=day,
          end_date=day,
          dimensions=dimensions,
          metrics=metrics,
          filters=filters,
          samplingLevel='HIGHER_PRECISION',
          max_results=max_results,
          start_index=start_index
      )
      rows = result.get('rows')

      if not rows:
        break
      if result.get('containsSampledData'):
        logging.warn('    sampled data returned for %s at starting index %i',
                     day, start_index)

      all_rows += rows
      start_index += max_results
      if start_index > result['totalResults']:
        break
    return all_rows


def send(params):
  """Sends a hit via Measurement Protocol.

  Args:
    params: dictionary with HTTP GET parameters of a hit.
  """
  clean_params = {k: params[k] for k in params if params[k] is not None}
  logging.debug(str(clean_params))
  if not ARGS.fake_sending:
    status = 404
    attempts_count = 0
    while status > 299 and attempts_count < 5:
      time.sleep(attempts_count * 5)
      response = urlfetch.get('https://www.google-analytics.com/collect',
                              params=clean_params)
      status = response.status
      attempts_count += 1
    if status > 299:
      raise urlfetch.UrlfetchException

