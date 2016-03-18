
import add, show, remove#, trigger

from openaps.cli.subcommand import Subcommand
from openaps.cli.commandmapapp import CommandMapApp

from trigger import Trigger

def get_trigger_map (conf):
  triggers = { }
  for trigger in Trigger.FromConfig(conf):
    triggers[trigger.name] = trigger
  return triggers

class TriggerAction (Subcommand):
  def setup_application (self):
    self.triggers = get_trigger_map(self.config)
    choices = self.triggers.keys( )
    choices.sort( )
    self.parser.add_argument('name', choices=choices)
    super(TriggerAction, self).setup_application( )

class TriggerManagement (CommandMapApp):
  """ triggers - manage triggers and triggers """
  Subcommand = TriggerAction
  name = 'action'
  title = '## Trigger management'

  def get_commands (self):
    return [add, show, remove]

class Exported (object):
  """ FOO """
  Configurable = Trigger
  @classmethod
  def get_map (Klass, conf):
    return get_trigger_map(conf)
  Command = TriggerManagement
  Subcommand = TriggerAction

