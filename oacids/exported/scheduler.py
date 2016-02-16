
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
import threading

class Trigger (GPropSync):
  OWN_IFACE = IFACE + '.Trigger'
  PROP_SIGS = {
    'name': 's'
  , 'obj': 's'
  , 'expected': 's'
  , 'phases': 's'
  , 'rrule': 's'
  , 'id': 's'
  , 'Status': 's'
  , 'countdown': 'd'
  }
  name = gobject.property(type=str)
  expected = gobject.property(type=str)
  obj = gobject.property(type=str)
  phases = gobject.property(type=str)
  rrule = gobject.property(type=str)
  trigger = gobject.property(type=str)
  _states = ['Armed', 'Running', 'Success', 'Error', 'Done', 'Gone' ]
  _error = [ ]
  @gobject.property(type=float)
  def countdown (self):
    return (self.when - datetime.datetime.now( )).total_seconds( )
  @gobject.property(type=str)
  def id (self):
    return self.armed.hashed
  @gobject.property(type=str)
  def Status (self):
    print "STATUS", self.id, self._states[self._status]
    return self._states[self._status]
  def __init__ (self, path, manager=None, props=None, armed=None):
    self.manager = manager
    bus = manager.bus
    self.bus = bus or dbus.SessionBus( )
    self.path = path
    self.when = armed.when
    self.armed = armed
    self._status = 0
    GPropSync.__init__(self, self.bus.get_connection( ), path)
    # WithProperties.__init__(self, self.bus.get_connection( ), path)
    self.attrs = props
    self.attrs['trigger'] = self.armed.hashed
    if props:
      for key in props:
        self.set_property(key, props[key])
    self.sync_all_props( )
  @dbus.service.signal(dbus_interface=OWN_IFACE,
                       signature='')
  def Armed (self):
    pass
  @dbus.service.signal(dbus_interface=OWN_IFACE,
                       signature='')
  def Running (self):
    self._status = 1
    pass
  @dbus.service.signal(dbus_interface=OWN_IFACE,
                       signature='')
  def Fire (self):
    now = datetime.datetime.now( )
    old = self.Status
    self._status = 1
    new = self.Status
    self.PropertiesChanged(self.OWN_IFACE, dict(Status=new), dict(Status=old))
    print "FIRED", now.isoformat( ), self.when.isoformat( ), self.name, self.path
    self.manager.Trigger("Queue", self.path)
    self.manager.master.background.Do(self.attrs, ack=self.on_success, error=self.on_error)
    # self._status += 1
  def on_error (self):
    print "PHASED ON ERROR"
    # self.Done( )
    self.Error( )
    pass 
  def on_success (self, results):
    print "RESULTS SUCCESS PHASE", results
    self._status = 2
    # self.Success( )
  @dbus.service.signal(dbus_interface=OWN_IFACE, signature='')
  def Success (self):
    self.PropertiesChanged(self.OWN_IFACE, dict(Status='Success'), dict(Status='Fired'))
    old_status = self.Status
    self._status = 2
    self.PropertiesChanged(self.OWN_IFACE, dict(Status='Success'), dict(Status=old_status))
    # self.Done( )
    pass
  @dbus.service.signal(dbus_interface=OWN_IFACE, signature='')
  def Error (self):
    self._status = 3
    self.PropertiesChanged(self.OWN_IFACE, dict(Status='Error'), dict(Status='Fired'))
    # self.Done( )
    pass
  @dbus.service.signal(dbus_interface=OWN_IFACE, signature='')
  def Done (self):
    old_status = self.Status
    # self._status += 1
    self._status = 4
    self.PropertiesChanged(self.OWN_IFACE, dict(Status='Done'), dict(Status=old_status))
    # self.Finish( )
    pass
  @dbus.service.signal(dbus_interface=OWN_IFACE, signature='')
  def Finish (self):
    self.PropertiesChanged(self.OWN_IFACE, dict(Status='Finish'), dict(Status='Done'))
    # self.Remove( )
    pass
  def phase (self, phase):
    phases = {
      'Running': self.Running
    , 'Done': self.Done
    , 'Error': self.Error
    , 'Finish': self.Finish
    , 'Success': self.Success
    , 'Remove': self.Remove
    }
    func = phases.get(phase, None)
    print "PHASE", phase, func, self.id
    if func:
      func( )
  @dbus.service.signal(dbus_interface=OWN_IFACE, signature='')
  def Remove (self):
    self._status = 5
    self.PropertiesChanged(self.OWN_IFACE, dict(Status='Remove'), dict())
    print "GOT REMOVE SIGNAL", self
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
      def cleaned ( ):
        self.manager.Trigger("Cleanup", self.trigger.path)
        self.manager.InterfacesRemoved(self.trigger.path, { Trigger.OWN_IFACE: self.props })
        self.remote.bus.remove_signal_receiver(self.cleanup, "Remove", dbus_interface=Trigger.OWN_IFACE, bus_name=BUS, path=self.trigger.path)
        self.trigger.remove_from_connection( )
      gobject.timeout_add(500, cleaned)


  def update_phase (self, signal, props):
    if props['expected'] == self.props['expected']:
      print "UPDATE PHASE", signal, props
  def arm (self, manager):
    self.manager = manager
    props = dict(obj=self.remote.path, name=self.remote.item.name, expected=self.when.isoformat( ), **self.remote.item.fields)
    self.props = props
    new_path = PATH + '/Scheduler/Armed/' + self.hashed
    delay_ms = (self.when - datetime.datetime.now( )).total_seconds( ) * 1000
    self.remote.bus.add_signal_receiver(self.cleanup, "Remove", dbus_interface=Trigger.OWN_IFACE, bus_name=BUS, path=new_path)
    # manager.bus.add_signal_receiver(self.attrs, ack=self.on_success, error=self.on_error)
    trigger = None
    try:
      trigger = Trigger(new_path, manager, props, self)
      if trigger:
        trigger.Armed( )
        self.manager.Trigger("Arming", trigger.path)
        self.trigger = trigger
        print "DELAYING", delay_ms
        gobject.timeout_add(delay_ms, trigger.Fire)
        manager.InterfacesAdded(trigger.path, { Trigger.OWN_IFACE: props })
        self.manager.Trigger("Armed", trigger.path)
    except:
      print "already exited?"
      raise
    finally:
      pass
    return trigger

class Scheduler (GPropSync, Manager):
  OWN_IFACE = IFACE + '.Scheduler'
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

  @dbus.service.signal(dbus_interface=OWN_IFACE,
                       signature='so')
  def Trigger (self, status, path):
    pass

  def Scan (self):
    candidates = self.Poll(within_seconds=self.TaskWithin)
    for candidate in candidates:
      # self.enqueue(candidate)
      # print candidate
      # print self.schedules
      
      is_armed = False
      other = self.schedules.get(candidate, None)
      found = 0
      added = 0
      if other is None:
        try:
          self.schedules[candidate] = candidate.arm(self)
          added += 1
          is_armed = True
        except Exception, e:
          print "what happened?", e
          pass
      else:
        found += 1
        pass
        # print "already scheduled", candidate
      txt = { True: "ARMED", False: "skipped" }
      # print txt.get(is_armed), candidate.when, candidate.remote.item.name, candidate.remote.path
    summary = """{dt}: tracking {num_schedules} managed, added {added} new, skipped {found} upcoming duplicates"""
    print summary.format(thread=threading.currentThread( ).ident, dt=datetime.datetime.now( ).isoformat( ), num_schedules=len(self.schedules), added=added, found=found)

    return 

  def Poll (self, within_seconds=None):
    # print "poll within", within_seconds
    results = [ ]
    candidates = self.master.openaps.things.get('schedules', [ ])
    now = datetime.datetime.now( )
    # print "polling schedules", len(candidates), now.isoformat( ), 'for', self.MaxTasksAhead, 'MaxTasksAhead'
    for configured in candidates:
      # print "SCHEDULE", configured.item.fields
      # spec = recurrent.parse(configured.item.fields['rrule'], now=self.since)
      spec = configured.item.fields['rrule']
      rr = rrule.rrulestr(spec, dtstart=self.since)
      # print configured.item.fields['rrule'], spec
      upcoming = rr.after(now)
      # print "next", upcoming.isoformat( )
      # XXX: bug in making: need to fill out all events before within_seconds as well.
      # if (upcoming - now).total_seconds( ) <= within_seconds:
      for upcoming in iter_triggers(upcoming, rr, within_seconds):
        # print "ARM THING", configured.path
        # print "ATTEMPT ARM", configured.item.name, configured.path, spec
        # self.enqueue(upcoming, configured)
        trigger = Armable(upcoming, configured)
        # exists = self.schedules[(upcoming, configured.item.name)]
        results.append(trigger)


    return results
    pass

  def GetTriggerById (self, hashed):
    for key, trigger in self.schedules.items( ):
      if trigger.id == hashed:
        return trigger
  def enqueue (self, upcoming, event):
    name = event.item.name
    obj_path = event.path
    isostr = upcoming.isoformat( )

    path = "%s/Trigger%s%s" % (self.path, name_title, len(self.schedules))

  def init_managed (self):
    self.since = utils.datetime.datetime.fromtimestamp(self.master.heartbeat.started_at)
    # self.add_signal_handler("heartbeat", self.Scan, dbus_interface=OPENAPS_IFACE + ".Heartbeat")
    print "SUBSCRIBING to Heartbeat"
    self.bus.add_signal_receiver(self.Scan, "Heartbeat", dbus_interface=OPENAPS_IFACE + ".Heartbeat", bus_name=BUS, path=self.master.heartbeat.path)

    # self.schedules = defaultdict(dict)
    self.schedules = { }
  def get_all_managed (self):
    paths = dict( )
    for thing in self.schedules:
      print thing
      spec = { thing.trigger.OWN_IFACE:  dict(**thing.trigger.GetAll(thing.trigger.OWN_IFACE)) }
      paths[thing.trigger.path] = spec
    return paths

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
def iter_triggers (upcoming, rule, within_seconds):
  end = upcoming + datetime.timedelta(seconds=within_seconds)
  while upcoming < end:
    yield upcoming
    upcoming = rule.after(upcoming)
