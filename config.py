"""Module that parses command line args and loads configuration from a file."""


import argparse
import logging
import os
import yaml


# Command line arguments parsing.
_parser = argparse.ArgumentParser()
_parser.add_argument('config_file',
                     help='Configuration JSON file')
_parser.add_argument('--skip_bootstrapping',
                     help='skip bootstrap DB queries',
                     action='store_true')
_parser.add_argument('--skip_extraction',
                     help='skip GA Core Reporting API data extraction',
                     action='store_true')
_parser.add_argument('--skip_processing',
                     help='skip data processing DB queries',
                     action='store_true')
_parser.add_argument('--skip_sending',
                     help='skip GA Measurement Protocol hits sending',
                     action='store_true')
_parser.add_argument('--fake_sending',
                     help='pretend to send GA Measurement Protocol hits',
                     action='store_true')
_parser.add_argument('--log_level',
                     help='logging level, defaults to INFO',
                     default='INFO')
ARGS = _parser.parse_args()

# Logging setup.
_log_level = getattr(logging, ARGS.log_level.upper(), None)
logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=_log_level)
logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)
logging.getLogger('oauth2client.client').setLevel(logging.WARNING)
logging.getLogger('oauth2client.crypt').setLevel(logging.WARNING)

# Loading configuration from a file.
if ARGS.config_file[0] == '/':
  _config_filename = ARGS.config_file
else:
  _config_filename = os.path.join(os.path.dirname(__file__), ARGS.config_file)
with open(_config_filename, 'rb') as _config_file:
  CFG = yaml.load(_config_file)


def main():
  pass


if __name__ == '__main__':
  main()
