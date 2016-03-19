
"""
emit - emit a trigger's events
"""
from oacids.exported.ifaces import BUS, IFACE, PATH, INTROSPECTABLE_IFACE, TRIGGER_IFACE
import pydbus
from pydbus import SystemBus
from trigger import Trigger
OWN_IFACE = IFACE + '.EventSink.Emitter'
def main (args, app):
  for trigger in Trigger.FromConfig(app.config):
    if args.name == trigger.name:
      with SystemBus( ) as bus:
        path = PATH + '/EventSink/{name:s}'.format(name=trigger.name)
        event = bus.get(BUS, path)
        event.Fire( )
        props = event.GetAll(OWN_IFACE)
        print props
