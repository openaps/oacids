
import dbus.service
from gi.repository import GObject as gobject

from oacids.helpers.dbus_props import GPropSync, Manager, WithProperties
from ifaces import BUS, IFACE, PATH, INTROSPECTABLE_IFACE, TRIGGER_IFACE, OPENAPS_IFACE

from oacids.schedules import utils
import datetime
from dateutil import parser, rrule, tz
import recurrent

from collections import deque, defaultdict
import hashlib

class Expected (GPropSync):
  OWN_IFACE = OPENAPS_IFACE + '.Expected'
  PROP_SIGS = {
    'name': 's'
  , 'obj': 's'
  , 'expected': 's'
  , 'phases': 's'
  , 'rrule': 's'
  , 'id': 's'
  }
  name = gobject.property(type=str)
  expected = gobject.property(type=str)
  obj = gobject.property(type=str)
  phases = gobject.property(type=str)
  rrule = gobject.property(type=str)
  id = gobject.property(type=str)
  def __init__ (self, path, manager=None, props=None):
    self.manager = manager
    bus = manager.bus
    self.bus = bus or dbus.SessionBus( )
    self.path = path
    GPropSync.__init__(self, self.bus.get_connection( ), path)
    # WithProperties.__init__(self, self.bus.get_connection( ), path)
    if props:
      for key in props:
        self.set_property(key, props[key])
    self.sync_all_props( )

  @dbus.service.signal(dbus_interface=OWN_IFACE,
                       signature='')
  def Fire (self):
    now = datetime.datetime.now( )
    print "FIRED", now.isoformat( ), self.expected
  @dbus.service.signal(dbus_interface=OWN_IFACE,
                       signature='')
  def Remove (self):
    pass
    

class Armable (object):
  def __init__ (self, when, remote):

    self.remote = remote
    self.when = when
    self.hashed = hashlib.sha224(remote.path + remote.item.name + when.isoformat( )).hexdigest( )

  def __hash__ (self):
    return hash((self.when.isoformat( ), self.remote.item.name, self.remote.path))
    # return hash(self.hashed)
  def __eq__ (self, other):
    return other.hashed == self.hashed
  def __cmp__ (self, other):
    if other.hashed == self.hashed:
      return 0
    a = ''.join([self.when.isoformat( ), self.remote.item.name, self.remote.path])
    b = ''.join([other.when.isoformat( ), other.remote.item.name, other.remote.path])
    if a > b:
      return 1
    else:
      return -1


  def cleanup (self):
    print "cleaning up"
    self.manager.schedules.pop(self)
    if self.trigger:
      self.manager.InterfacesRemoved(self.trigger.path, { Expected.OWN_IFACE: self.props })
      self.trigger.remove_from_connection( )


  def arm (self, manager):
    self.manager = manager
    props = dict(obj=self.remote.path, name=self.remote.item.name, expected=self.when.isoformat( ), **self.remote.item.fields)
    self.props = props
    new_path = PATH + '/Trigger/' + self.hashed
    delay_ms = (self.when - datetime.datetime.now( )).total_seconds( ) * 1000
    self.remote.bus.add_signal_receiver(self.cleanup, "Fire", dbus_interface=Expected.OWN_IFACE, bus_name=BUS, path=new_path)
    trigger = None
    try:
      trigger = Expected(new_path, manager, props)
      if trigger:
        self.trigger = trigger
        print "DELAYING", delay_ms
        gobject.timeout_add(delay_ms, trigger.Fire)
        manager.InterfacesAdded(trigger.path, { Expected.OWN_IFACE: props })
    except:
      print "already exited?"
      raise
    finally:
      pass
    return trigger

class Scheduler (GPropSync, Manager):
  OWN_IFACE = OPENAPS_IFACE + '.Scheduler'
  PROP_SIGS = {
    'TaskWithin': 'd'
  , 'MaxTasksAhead': 'u'
  }
  TaskWithin = gobject.property(type=float)
  MaxTasksAhead = gobject.property(type=int, default=5)
  def __init__ (self, bus, ctrl):
    self.bus = bus
    self.path = PATH + '/Scheduler'
    self.master = ctrl
    Manager.__init__(self, self.path, bus)
    self.TaskWithin = (self.master.heartbeat.interval * self.MaxTasksAhead) / 1000
    self.init_managed( )


  def Scan (self):
    candidates = self.Poll(within_seconds=self.TaskWithin)
    for candidate in candidates:
      # self.enqueue(candidate)
      print candidate
      print self.schedules
      
      other = self.schedules.get(candidate, None)
      if other is None:
        self.schedules[candidate] = candidate.arm(self)

    return 

  def Poll (self, within_seconds=None):
    # print "poll within", within_seconds
    results = [ ]
    candidates = self.master.openaps.things.get('schedules', [ ])
    now = datetime.datetime.now( )
    print "polling schedules", len(candidates), now.isoformat( ), 'for', self.MaxTasksAhead, 'MaxTasksAhead'
    for configured in candidates:
      # print "SCHEDULE", configured.item.fields
      # spec = recurrent.parse(configured.item.fields['rrule'], now=self.since)
      spec = configured.item.fields['rrule']
      rr = rrule.rrulestr(spec, dtstart=self.since)
      print configured.item.name, configured.path, spec
      # print configured.item.fields['rrule'], spec
      upcoming = rr.after(now)
      # print "next", upcoming.isoformat( )
      if (upcoming - now).total_seconds( ) <= within_seconds:
        print "ARM THING", configured.path
        # self.enqueue(upcoming, configured)
        trigger = Armable(upcoming, configured)
        # exists = self.schedules[(upcoming, configured.item.name)]
        results.append(trigger)


    return results
    pass

  def enqueue (self, upcoming, event):
    name = event.item.name
    obj_path = event.path
    isostr = upcoming.isoformat( )

    path = "%s/Trigger%s%s" % (self.path, name_title, len(self.schedules))

  def init_managed (self):
    self.since = utils.datetime.datetime.fromtimestamp(self.master.heartbeat.started_at)
    # self.add_signal_handler("heartbeat", self.Scan, dbus_interface=OPENAPS_IFACE + ".Heartbeat")
    self.bus.add_signal_receiver(self.Scan, "heartbeat", dbus_interface=OPENAPS_IFACE + ".Heartbeat", bus_name=BUS, path=self.master.heartbeat.path)

    # self.schedules = defaultdict(dict)
    self.schedules = { }
  def get_all_managed (self):
    paths = dict( )
    for thing in self.schedules:
      print thing
      spec = { thing.OWN_IFACE:  dict(**thing.GetAll(thing.OWN_IFACE)) }
      paths[thing.path] = spec
    return paths
    managed = self.schedules
    return managed
  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='a{sv}', out_signature='')
                       # , async_callbacks=('ack', 'error'))
  # def Create (self, props, ack=None, error=None):
  def Create (self, props):
    path = "%s/Trigger%s" % (self.path, len(self.schedules))
    new_schedule = Trigger(path, self.bus, props)
    print "NEW SCHEDULE", new_schedule
    self.schedules.append(new_schedule)
    self.InterfacesAdded(path, { TRIGGER_IFACE: props })
