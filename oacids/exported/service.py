
import os
import dbus.service
from gi.repository import GObject as gobject

from oacids.helpers.dbus_props import GPropSync, Manager, WithProperties
from ifaces import BUS, IFACE, PATH, INTROSPECTABLE_IFACE, TRIGGER_IFACE
import managed
import heartbeat
import scheduler
import doable
import triggers

"""
class Trigger (GPropSync):
  OWN_IFACE = TRIGGER_IFACE
  PROP_SIGS = {
    'name': 's'
  }
  name = gobject.property(type=str)
  def __init__ (self, path, bus=None, props=None):
    self.bus = bus or dbus.SystemBus( )
    self.path = path
    WithProperties.__init__(self, self.bus.get_connection( ), path)
    if props:
      for key in props:
        self.set_property(key, props[key])
    self.sync_all_props( )
  @dbus.service.method(dbus_interface=TRIGGER_IFACE,
                       in_signature='', out_signature='',
                       async_callbacks=('ack', 'error'))
  def Remove (self, ack=None, error=None):
    ack( )
"""

class ScheduleManager (Manager):
  def __init__ (self, bus, path):
    self.bus = bus
    self.path = path
    Manager.__init__(self, path, bus)
  def init_managed (self):
    return
    self.schedules = [ ]
  """
  def get_all_managed (self):
    paths = dict( )
    for thing in self.schedules:
      print thing
      spec = { thing.OWN_IFACE:  dict(**thing.GetAll(thing.OWN_IFACE)) }
      paths[thing.path] = spec
    return paths
    managed = self.schedules
    return managed
  @dbus.service.method(dbus_interface=IFACE,
                       in_signature='a{sv}', out_signature='')
                       # , async_callbacks=('ack', 'error'))
  # def Create (self, props, ack=None, error=None):
  def Create (self, props):
    path = "%s/Trigger%s" % (self.path, len(self.schedules))
    new_schedule = Trigger(path, self.bus, props)
    print "NEW SCHEDULE", new_schedule
    self.schedules.append(new_schedule)
    self.InterfacesAdded(path, { TRIGGER_IFACE: props })

  """

class NaiveService (ScheduleManager, GPropSync):
    openaps = None
    OWN_IFACE = IFACE
    PROP_SIGS = {
      'fuel': 'i'
    , 'blah': 's'
    , 'name': 's'
    , 'Name': 's'
    , 'mode': 's'
    , 'status': 'u'
    , 'ini_home': 's'
    , 'homedir': 's'
    }
    blah = gobject.property(type=str)
    homedir = gobject.property(type=str, default=".")
    mode = gobject.property(type=str, flags=gobject.PARAM_READABLE, default='foo')
    heartbeat = None

    @gobject.property(type=int, default=0)
    def status (self):
      """ Status """

      return 0

    # describe_property(dbus_interface=IFACE, type_signature='s') ()
    name = gobject.property(type=str)
    @gobject.property(type=str)
    def Name (self):
      return self.name
    @gobject.property(type=str)
    def ini_home (self):
      return self.homedir
    @ini_home.setter
    def set_ini_home (self, value):
      directory = os.path.realpath(os.path.expanduser(value))
      print "NEW HOME", value, directory, os.path.isdir(directory)
      if not os.path.exists(directory) or not os.path.isdir(directory):
        # raise Exception("Not a directory: %s" % directory)
        raise dbus.exceptions.DBusException(
            self.OWN_IFACE,
            'Directory does not exist, failed to set ini_home to: %s.'
                % directory)
      os.chdir(directory)
      if self.openaps:
        self.InterfacesRemoved(self.openaps.path, self.openaps.GetAll(self.openaps.OWN_IFACE))
        self.openaps.remove_from_connection( )
      self.openaps = managed.Instance(self.bus, self)
      self.InterfacesAdded(self.openaps.path, self.openaps.GetAll(self.openaps.OWN_IFACE))
      self.homedir = directory
    def __init__ (self, loop, bus=None, path=PATH):
        self.loop = loop
        self.bus = bus or dbus.SystemBus( )
        self.path = path
        request = self.bus.request_name(BUS, dbus.bus.NAME_FLAG_DO_NOT_QUEUE)
        self.running = False
        ScheduleManager.__init__(self, self.bus, PATH)
        self.sync_all_props( )
        self.init_managed( )
        self.ResetHeartbeat( )
        self.scheduler = scheduler.Scheduler(self.bus, self)
        self.background = doable.Doable(self)
        self.eventsink = triggers.EventSink(self.bus, self)
        # self.connect("notify::ini-home", self.on_change_home)

    def get_all_managed (self):
      things = filter(lambda x: x, [self.background, self.scheduler, self.heartbeat, self.openaps])
      paths = dict( )
      # for thing in self.schedules:
      for thing in things:
        print thing
        spec = { thing.OWN_IFACE:  dict(**thing.GetAll(thing.OWN_IFACE))
               , dbus.INTROSPECTABLE_IFACE:  dict( )
               , dbus.PROPERTIES_IFACE:  dict( ) }
        #if hasattr(thing, 'GetManagedObjects'): spec['org.freedesktop.DBus.ObjectManager']
        paths[thing.path] = spec
      return paths

    @dbus.service.method(dbus_interface=IFACE,
                         in_signature='i',
                         out_signature='i',
                         async_callbacks=('reply_handler',
                                          'error_handler'))
    def Delay (self, seconds, reply_handler, error_handler):
        print "Sleeping for %ds" % seconds
        gobject.timeout_add_seconds (seconds,
                                     lambda: reply_handler (seconds))

    @dbus.service.method(dbus_interface=IFACE,
                         in_signature='', out_signature='')
    def ResetHeartbeat (self):
      if self.heartbeat:
        self.heartbeat.Stop( )
        self.heartbeat.remove_from_connection( )
      self.heartbeat = heartbeat.Heartbeat(self.bus, self)
      print "Set up HEARTBEAT!", self.heartbeat

    @dbus.service.method(dbus_interface=IFACE,
                         in_signature='', out_signature='')
    def Howdy(self):
      print "Howdy!"

    @dbus.service.method(dbus_interface=IFACE,
                         in_signature='', out_signature='s')
    def Start (self):
      print "Howdy!"
      return "OK"
    @dbus.service.signal(dbus_interface=OWN_IFACE,
                         signature='')
    def Quit (self):
      gobject.timeout_add(2, self.loop.quit)
      # self.loop.quit()
