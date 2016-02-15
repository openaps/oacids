
from oacids.helpers.dbus_props import GPropSync, Manager, WithProperties
import dbus.service
from gi.repository import GObject as gobject
import dbus
import types
from ifaces import IFACE, PATH, OPENAPS_IFACE, BUS, TRIGGER_IFACE


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

def get_trigger_for (path, scheduler):
  if path:
    return scheduler.GetTriggerById(path)
    proxy = bus.get_object(BUS, path)
    iface = dbus.Interface(proxy, TRIGGER_IFACE)
    return iface
def update_phase (trigger, phase):
  _states = ['Armed', 'Running', 'Done', 'Gone' ]
  # Armed, Fire
  # Running
  # Success, Error, Done, Remove
  # print trigger
  if trigger:
    trigger.phase(phase)
    # if func: print "PHASING", phase func( )
    pass
  pass

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
      # print "ALL SCHEDULED", manager.master.scheduler.schedules
      trigger = get_trigger_for(item.get('trigger', None), manager.master.scheduler)
      print "FROM TRIGGER", trigger
      # http://stackoverflow.com/questions/5943249/python-argparse-and-controlling-overriding-the-exit-status-code
      fuzz = dbus.Dictionary(item, signature="sv")
      # fuzz.update(**item)
      manager.Phase('get', fuzz);
      update_phase(trigger, 'Running')
      try:
        app = DoTool.Make(item)
        manager.Phase('make', fuzz);
        print "GOT ITEM", item, app
        results = app( )
        update_phase(trigger, 'Success')
        manager.Phase('success', fuzz);
        on_ack(results)

      except (Exception, SystemExit), e:
        print "EXCEPTINO!!!!"
        print e
        manager.Phase('error', fuzz);
        update_phase(trigger, 'Error')
        time.sleep(0.150)
        on_error( )
        if e:
          traceback.print_exc(file=sys.stdout)
          # traceback.print_last( )
      finally:

        # update_phase(trigger, 'Done')
        # update_phase(trigger, 'Finish')
        update_phase(trigger, 'Remove')
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
