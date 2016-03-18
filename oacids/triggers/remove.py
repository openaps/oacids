
"""
remove - remove a trigger
"""
from trigger import Trigger
def main (args, app):
  for trigger in Trigger.FromConfig(app.config):
    if args.name == trigger.name:
      trigger.remove(app.config)
      app.config.save( )
      print 'removed', trigger.format_url( )
      break

