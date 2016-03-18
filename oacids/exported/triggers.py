
import dbus.service
from gi.repository import GObject as gobject

from oacids.helpers.dbus_props import GPropSync, Manager, WithProperties, ObjectManager
from ifaces import BUS, IFACE, PATH, INTROSPECTABLE_IFACE, TRIGGER_IFACE, OPENAPS_IFACE

EVENT_IFACE = 'org.openaps.Service.Instance.Triggers'

class Emitter (GPropSync):
  OWN_IFACE = IFACE + '.EventSink.Emitter'
  PATH_TEMPLATE = PATH + '/EventSink/{name:s}'
  def __init__ (self, path, manager=None, props=None):
    self.manager = manager
    bus = manager.bus
    self.bus = bus or dbus.SessionBus( )
    self.path = path
    # self.when = armed.when
    # self.armed = armed
    GPropSync.__init__(self, self.bus.get_connection( ), path)
    # WithProperties.__init__(self, self.bus.get_connection( ), path)
    self.attrs = props

  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='', out_signature='')
  def Fire (self):
    self.Emit('Fire')
    self.Do( )
  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='a{sv}', out_signature='')
  def Update (self, props):
    print props
  @dbus.service.signal(dbus_interface=OWN_IFACE,
                       signature='s')
  def Emit (self, status):
    print status
  @dbus.service.signal(dbus_interface=OWN_IFACE,
                       signature='')
  def Do (self):
    print self.manager.master.background.Do
    def response (*args):
      print "RESPONSE", args
    then = self.attrs['then']
    command = dict(name=self.attrs['name'], phases="")
    self.manager.master.background.Do(command, ack=response, error=response)
    if then:
      command = dict(name=then, phases="")
      self.manager.master.background.Do(command, ack=response, error=response)

class EventSink (GPropSync, Manager):
  OWN_IFACE = IFACE + '.EventSink'
  PROP_SIGS = {

  }
  def __init__ (self, bus, ctrl):
    self.bus = bus
    self.path = PATH + '/EventSink'
    self.master = ctrl
    self.events = [ ]
    Manager.__init__(self, self.path, bus)
    self.init_managed( )

  def init_managed (self):
    # self.since = utils.datetime.datetime.fromtimestamp(self.master.heartbeat.started_at)
    # self.add_signal_handler("heartbeat", self.Scan, dbus_interface=OPENAPS_IFACE + ".Heartbeat")
    print "SUBSCRIBING to master's Interfaces events"
    self.bus.add_signal_receiver(self.AddEvent, "InterfacesAdded", dbus_interface=ObjectManager, bus_name=BUS)
    self.bus.add_signal_receiver(self.RemoveEvent, "InterfacesRemoved", dbus_interface=ObjectManager, bus_name=BUS)

  def get_all_managed (self):
    paths = dict( )
    for thing in self.events:
      # print thing, thing.trigger.OWN_IFACE
      # print thing.trigger.OWN_IFACE, thing.trigger
      spec = { thing.trigger.OWN_IFACE:  dict(**thing.trigger.GetAll(thing.trigger.OWN_IFACE)) }
      paths[thing.trigger.path] = spec
    return paths

  def AddEvent (self, path, spec):
    if path.startswith('/org/openaps/Services/Instance/Trigger'):
      print "FOUND NEW", path, spec
      props = spec[EVENT_IFACE]
      name = props.get('name')
      then = props.get('then')
      print name, then
      self.Create(props)

  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='a{sv}', out_signature='')
  def Create (self, props):
    emitter = Emitter(Emitter.PATH_TEMPLATE.format(**props), self, props)
    self.InterfacesAdded(emitter.path, emitter.GetAll(emitter.OWN_IFACE))
    self.events.append(emitter)


  def RemoveEvent (self, path, props):
    if path.startswith('/org/openaps/Services/Instance/Trigger'):
      print "REMOVED", path, props

  @dbus.service.signal(dbus_interface=ObjectManager,
                       signature='oa{sa{sv}}')
  def InterfacesAdded (self, path, iface_spec):
    pass

  @dbus.service.signal(dbus_interface=ObjectManager,
                       signature='oas')
  def InterfacesRemoved (self, path, iface_spec):
    pass
