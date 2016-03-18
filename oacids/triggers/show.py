
"""
show   - show all trigger
"""

from openaps.cli import helpers
from trigger import Trigger

def configure_app (app, parser):
  parser.set_defaults(name='*')
  parser._actions[-1].nargs = '?'
  if parser._actions[-1].choices:
    parser._actions[-1].choices.append('*')
  helpers.install_show_arguments(parser)

def main (args, app):
  for device in Trigger.FromConfig(app.config):
    if args.name in [ '*', device.name ]:
      print args.format(device)

