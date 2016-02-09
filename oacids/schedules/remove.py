
"""
remove - remove a schedule
"""
from schedule import Schedule
def main (args, app):
  for schedule in Schedule.FromConfig(app.config):
    if args.name == schedule.name:
      schedule.remove(app.config)
      app.config.save( )
      print 'removed', schedule.format_url( )
      break

