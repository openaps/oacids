
import os
import time
import dbus.service
from gi.repository import GObject as gobject

from datetime import datetime
from oacids.helpers.dbus_props import GPropSync, Manager, WithProperties
from ifaces import BUS, IFACE, PATH, INTROSPECTABLE_IFACE, TRIGGER_IFACE, OPENAPS_IFACE

# class Heartbeat (GPropSync, Manager):
class Heartbeat (GPropSync):
  OWN_IFACE = OPENAPS_IFACE + '.Heartbeat'
  active = False
  sleep_interval = 1000
  started_at = None
  def __init__ (self, bus, ctrl):
    self.bus = bus
    self.path = PATH + '/Heartbeat'
    self.master = ctrl
    self.started_at = time.time( )
    self.now = datetime.fromtimestamp(self.started_at)
    GPropSync.__init__(self, bus, self.path)
    self.handle = None
    self.Start( )

  PROP_SIGS = {
    'interval': 'u'
  , 'Ticking': 'b'
  , 'StartedAt': 'd'
  , 'Uptime': 'd'
  }

  @gobject.property(type=int, default=1000)
  def interval (self):
    return self.sleep_interval

  @gobject.property(type=bool, default=False)
  def Ticking (self):
    return self.active

  @gobject.property(type=float)
  def StartedAt (self):
    return self.started_at

  @gobject.property(type=float)
  def Uptime (self):
    return time.time( ) - self.started_at



  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='u', out_signature='s')
  def Start (self, ms=1000):
      self.active = True
      self.sleep_interval = ms
      self.handle = gobject.timeout_add(self.interval, self._tick)
    

  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='', out_signature='s')
  def Stop (self):
      gobject.source_remove (self.handle)
      self.active = False
      self.handle = None
    

  @dbus.service.signal(dbus_interface=OWN_IFACE,
                       signature='')
  def Heartbeat (self):
      print "scanning"
      pass
      # print "Heartbeat Still alive at", self.Uptime
  def _tick (self):
      self.Heartbeat( )
      return self.Ticking
