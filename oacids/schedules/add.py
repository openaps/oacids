
"""
add   - add a scheduled event
"""

from schedule import Schedule
import sys

def configure_app (app, parser):
  parser._actions[-1].choices = None
  # TODO: more schedule minting/preview options
  # --phases
  # --phases
  parser.add_argument('--preview', '-n',  default=False, action='store_true', help='No op: preview phrase like "every 5 minutes".')
  parser.add_argument('rrule',  type=Schedule.parse_rrule, help='Schedule specification, like "every 5 minutes".')

def main (args, app):
  if not args.rrule:
    msg = "Could not parse rrule specification: %s" % ' '.join(sys.argv[3:])
    print "Error:", msg
    raise Exception(msg)
  new_schedule = Schedule(name=args.name, rrule=args.rrule, phases=' '.join([ ]))
  if not args.preview:
    new_schedule.store(app.config)
    app.config.save( )
  print "added", new_schedule.format_url( )

