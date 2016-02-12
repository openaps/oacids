
from subprocess import call
import shlex
import random
import time
import openaps.cli
import argcomplete

from openaps import builtins
from openaps import alias
from openaps import reports
from openaps import devices
from openaps import uses

MAP = {
  'report': reports
}

class TODOFixARGV (openaps.cli.ConfigApp):
  def __call__ (self):
    self.prep_parser( )
    self.configure_parser(self.parser)
    argcomplete.autocomplete(self.parser, always_complete_options=self.always_complete_options);
    # print "FIXED INPUTS??", self.inputs
    self.args = self.parser.parse_args(self.inputs)
    self.prolog( )
    self.run(self.args)
    self.epilog( )


class WrappedReports (TODOFixARGV):
  """ report - reusable reports

  """
  # XXX: mostly copied from bin/openaps-report
  name = 'report'
  def configure_parser (self, parser):
    self.read_config( )
    available = devices.get_device_map(self.config)
    self.devices = available
    choices = available.keys( )
    choices.sort( )
    # self.parser.add_argument('--version', action='version', version='%s %s' % ('%(prog)s', openaps.__version__))

    self.configure_reports( )

  def configure_reports (self):
    self.actions = reports.ReportManagementActions(parent=self)
    self.actions.configure_commands(self.parser)
  def configure_devices (self):
    allowed = [ ]
    self.commands = uses.UseDeviceCommands(self.devices, parent=self)
    self.commands.configure_commands(self.parser)
  def prolog (self):
    super(WrappedReports, self).prolog( )
    print "PROLOG"

  def epilog (self):
    print "EPILOG"
    # super(ReportToolApp, self).epilog( )

  def run (self, args):
    # print "WRAPPED", self.inputs
    # print "WRAPPED", args
    app = self.actions.selected(args)
    output = app(args, self)
    print "OUTPUT:"
    print output

class WrappedAlias (object):
  """ tool for running alias from code


  """
  name = 'alias'
  def __init__ (self, spec):
    # self.parent = parent
    self.spec = spec
  def configure_parser (self, parser):
    parser.add_argument('--bash', '-c', nargs='*')
    parser.add_argument('command', nargs='*')
    # parser.add_argument('args', nargs='*')
    # self.read_config( )
  def epilog (self):
    print "EPILOG"
  def __call__ (self):
    # print "ALIAS inner WRAPPED", self.spec


    spec_command = shlex.split(' '.join(self.spec))
    # print "CALLING", spec_command
    return call(spec_command)


def Missing (args):
  raise NotImplemented("unknown: %s" % ' '.join(args))

class Runner (object):
  MAP = {
    'report': WrappedReports
  , '!': WrappedAlias
  }
  def __init__ (self, spec):
    self.spec = spec
    self.command = spec.fields['command']
    self.prefix = self.command.split(' ')[:1].pop( )
    self.tail = self.command.split(' ')[1:]

  def main (self, parent, args):
    method = self.MAP.get(self.prefix, Missing)
    print self.prefix, "inner main running", self.command, self.tail

    app = method(self.tail)
    out = app( )
    print "ran app and got", app, out
    

class DoTool (TODOFixARGV):
  """ do - a tool for doing openaps commands


  """

  def configure_parser (self, parser):
    candidates = builtins.get_builtins( )
    self.candidates = candidates
    choices = candidates.keys( )
    choices.sort( )
    # print candidates
    parser.add_argument('commands', nargs='*',  choices=choices)
    # parser.add_argument('remainder', nargs='*', default='')
  @classmethod
  def Make (Klass, spec):
    cmd = "{name} {phases}".format(**spec).strip( )
    print cmd, spec
    app = DoTool(cmd.split(' '))
    return app

  def run (self, args):
    print "INPUTS", self.inputs
    print "RUNNING", args
    for command in args.commands:
      current = self.candidates[command]
      print current.name, current.fields
      runner = Runner(current)
      results = runner.main(self, args)
      # help(current)
    sleepr = random.randrange(100.0, 4000.0) / 1000.0
    print "sleeping", sleepr
    time.sleep(sleepr)
    return "HA"

if __name__ == '__main__':
  import sys
  app = DoTool(None)
  app( )
