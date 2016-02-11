
from oacids.helpers.dbus_props import GPropSync, Manager, WithProperties
import dbus.service
from gi.repository import GObject as gobject
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
    self.thread = Thread(target=self.run)
    self.thread.daemon = True
    self.thread.start( )
    print "started", self.thread
    self.running = True
  def run (self):
    print "running", self, self.running
    while self.running or not self.Q.empty( ):
      item = self.Q.get( )
      results = None
      # http://stackoverflow.com/questions/5943249/python-argparse-and-controlling-overriding-the-exit-status-code
      try:
        app = DoTool.Make(item)
        print "GOT ITEM", item, app
        results = app( )
      except (SystemExit), e:
        print "EXCEPTINO!!!!", "argparse fail?"
      except (Exception), e:
        print "EXCEPTINO!!!!"
        print e
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
                       in_signature='a{sv}', out_signature='s')
  def Do (self, params):
    print "DO!", params
    self.Q.put(params)
    return "OK"

  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='', out_signature='s')
  def Shutdown (self):
    self.Q.join( )
    self.background.stop( )
    return "OK"

  @dbus.service.signal(dbus_interface=OWN_IFACE,
                       signature='')
  def FOOBAR (self):
    pass
    # gobject.timeout_add(2, self.loop.quit)
    # self.loop.quit()
