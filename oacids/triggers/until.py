
"""
until - wait until a trigger emits events
"""
from oacids.exported.ifaces import BUS, IFACE, PATH, INTROSPECTABLE_IFACE, TRIGGER_IFACE
import pydbus
from pydbus import SystemBus
from trigger import Trigger
OWN_IFACE = IFACE + '.EventSink.Emitter'
from gi.repository import GLib

from threading import Thread, Event
import sys

class WaitApp (object):
  def __init__ (self):
    # self.event = event
    self.ev = Event( )
    self.loop = GLib.MainLoop( )
    self.expired = False

  def handle_emitted (self, status):
    print "emitted", status, self

  def handle_event (self):
    print "event", self.loop
    self.loop.quit( )


  def until (self, event, timeout=None):
    self.event = event
    self.event.Do.connect(self.handle_event)
    self.event.Emit.connect(self.handle_emitted)
    self.background = Thread(target=self.pending, args=(timeout, self.loop.quit))
    self.background.daemon = True
    self.background.start( )
    self.loop.run( )

  def pending (self, timeout, quit):
    print "starting background, waiting for ", timeout
    self.ev.wait(timeout)
    quit( )
    self.expired = True
    print "Failed to find event within", timeout


def configure_app (app, parser):
  parser.add_argument('--seconds', type=float)

def main (args, app):
  wait = WaitApp( )
  for trigger in Trigger.FromConfig(app.config):
    if args.name == trigger.name:
      with SystemBus( ) as bus:
        path = PATH + '/EventSink/{name:s}'.format(name=trigger.name)
        event = bus.get(BUS, path)

        props = event.GetAll(OWN_IFACE)
        print props
        wait.until(event, timeout=args.seconds)
  if wait.expired:
    sys.exit(2)
  

