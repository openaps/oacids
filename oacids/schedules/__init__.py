
import add, show, remove#, trigger

from openaps.cli.subcommand import Subcommand
from openaps.cli.commandmapapp import CommandMapApp

from schedule import Schedule

def get_schedule_map (conf):
  schedules = { }
  for sched in Schedule.FromConfig(conf):
    schedules[sched.name] = sched
  return schedules

class ScheduleAction (Subcommand):
  def setup_application (self):
    self.schedules = get_schedule_map(self.config)
    choices = self.schedules.keys( )
    choices.sort( )
    self.parser.add_argument('name', choices=choices)
    super(ScheduleAction, self).setup_application( )

class ScheduleManagement (CommandMapApp):
  """ schedules - manage schedules and triggers """
  Subcommand = ScheduleAction
  name = 'action'
  title = '## Schedule management'

  def get_commands (self):
    return [add, show, remove]

class Exported (object):
  """ FOO """
  Configurable = Schedule
  @classmethod
  def get_map (Klass, conf):
    return get_schedule_map(conf)
  Command = ScheduleManagement
  Subcommand = ScheduleAction
