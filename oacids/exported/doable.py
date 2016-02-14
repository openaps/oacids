
from oacids.helpers.dbus_props import GPropSync, Manager, WithProperties
import dbus.service
from gi.repository import GObject as gobject
import dbus
import types
from ifaces import IFACE, PATH, OPENAPS_IFACE


from oacids.schedules import utils
import datetime
from dateutil import parser, rrule, tz
import recurrent

from Queue import Queue
from threading import Thread
# from collections import deque, defaultdict
import random
import time

from oacids.tools import do
import openaps.cli
import argcomplete
import traceback
import sys

DoTool = do.DoTool


class Task (object):
  def __init__ (self, manager, Q):
    self.manager = manager
    self.running = True
    self.Q = Q

  def start (self):
    self.thread = Thread(target=self.run, args=(self.manager, self.Q))
    self.thread.daemon = True
    self.thread.start( )
    print "started", self.thread
    self.running = True
  def run (self, manager, Q):
    print "running", self, self.running
    while self.running or not self.Q.empty( ):
      item, callbacks = self.Q.get( )
      on_ack, on_error = callbacks
      print "GOT FROM Q", item
      results = None
      # http://stackoverflow.com/questions/5943249/python-argparse-and-controlling-overriding-the-exit-status-code
      fuzz = dbus.Dictionary(signature="sv")
      fuzz.update(**item)
      manager.Phase('get', fuzz);
      try:
        app = DoTool.Make(item)
        manager.Phase('make', fuzz);
        print "GOT ITEM", item, app
        results = app( )
        manager.Phase('success', fuzz);
        on_ack(results)
      except (SystemExit), e:
        print "EXCEPTINO!!!!", "argparse fail?"
        manager.Phase('error', fuzz);
        on_error( )
      except (Exception), e:
        print "EXCEPTINO!!!!"
        print e
        manager.Phase('error', fuzz);
        on_error( )
        if e:
          traceback.print_exc(file=sys.stdout)
          # traceback.print_last( )

      print "DONE", results
      self.Q.task_done( )

  def stop (self):
    self.running = False 

class Doable (GPropSync, Manager):
  OWN_IFACE = IFACE + '.Do'
  PROP_SIGS = {
    'MaxTasksQueue': 'u'
  }
  MaxTasksQueue = gobject.property(type=int, default=0)
  def __init__ (self, ctrl):
    self.bus = bus = ctrl.bus
    self.path = PATH + '/Do'
    self.master = ctrl
    Manager.__init__(self, self.path, bus)
    self.sync_all_props( )

    self.init_managed( )
  def init_managed (self):
    self.Q = Queue(self.MaxTasksQueue)
    self.background = Task(self, self.Q)
    self.background.start( )
    self.tasks = dict( )
  def get_all_managed (self):
    results = dict( )
    return results

  @dbus.service.method(dbus_interface=OWN_IFACE,
                       async_callbacks=('ack', 'error'),
                       in_signature='a{sv}', out_signature='s')
  def Do (self, params, ack=None, error=None):
    fuzz = dbus.Dictionary(signature="sv")
    fuzz.update(**params)
    self.Phase('put', fuzz);
    print "DO!", params
    self.Q.put((params, (ack, error)))
    return "OK"

  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='', out_signature='s')
  def Shutdown (self):
    self.Q.join( )
    self.background.stop( )
    return "OK"

  @dbus.service.signal(dbus_interface=OWN_IFACE,
                       signature='sa{sv}')
  def Phase (self, status, props):
    pass
  @dbus.service.signal(dbus_interface=OWN_IFACE,
                       signature='')
  def FOOBAR (self):
    pass
    # gobject.timeout_add(2, self.loop.quit)
    # self.loop.quit()
