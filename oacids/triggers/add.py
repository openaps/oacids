

"""
add   - add a managed Trigger
"""

from trigger import Trigger
import sys
import argparse

def configure_app (app, parser):
  parser._actions[-1].choices = None
  parser.add_argument('--preview', '-n',  default=False, action='store_true', help='No op: preview phrase like "every 5 minutes".')
  parser.add_argument('then', nargs=argparse.REMAINDER, default="", help='Trigger specification, like "report invoke foobar.json".')

def main (args, app):
  print args

  new_trigger = Trigger(name=args.name, then=' '.join(args.then))
  if not args.preview:
    new_trigger.store(app.config)
    app.config.save( )
  print "added", new_trigger.format_url( )

