
import openaps

from oacids.helpers.dbus_props import GPropSync, Manager, WithProperties
import dbus.service
from gi.repository import GObject as gobject
import types
from ifaces import IFACE, PATH, OPENAPS_IFACE

import openaps.cli
import openaps.devices
import openaps.reports
import openaps.vendors.plugins
import openaps.alias

class Instance (GPropSync, Manager, openaps.cli.ConfigApp):
  OWN_IFACE = OPENAPS_IFACE
  def __init__ (self, bus, ctrl):
    self.bus = bus
    self.path = PATH + '/Instance'
    self.master = ctrl
    Manager.__init__(self, self.path, bus)
    self.sync_all_props( )
    self.read_config( )

    self.init_backends( )
    """
    self.backends = configurable_entries( )
    self.devices = Devices.LookUp(self, announce=True )
    self.reports = Reports.LookUp(self, announce=True )
    self.alias = Alias.LookUp(self, announce=True )
    self.vendors = Vendors.LookUp(self, announce=True )
    """

  def init_backends (self):
    self.backends = configurable_entries( )
    self.things = dict( )
    for key in self.backends:
      Thing = self.backends[key]
      things = Thing.LookUp(self, announce=True)
      self.things[key] = things

  def get_all_managed (self):

    things = dict( )
    for key in self.things:
      things.update(**self.GetSpecs(self.things[key]))
    return things

    things.update(**self.GetSpecs(self.devices))
    things.update(**self.GetSpecs(self.reports))
    things.update(**self.GetSpecs(self.alias))
    things.update(**self.GetSpecs(self.vendors))
    return things
    return [ ] + self.GetSpecs(self.devices) + self.GetSpecs(self.reports) + self.GetSpecs(self.alias) + self.GetSpecs(self.vendors)

  def get_devices (self, announce=False):
    specs = [ ]
    for device in self.devices:
      print device.OWN_IFACE
      print device.item.fields
      spec = { device.OWN_IFACE: dict(name=device.item.name, **device.item.fields) }
      specs.append({ device.path: [ spec ] })
    print "DEVICES DBUS SPEC", specs
    return specs
  def lookup_devices (self, announce=False):
    devices = Devices.FromParent(self)
    for device in devices:
      if announce:
        print device.OWN_IFACE
        print device.item.fields
        spec = { device.OWN_IFACE: dict(name=device.item.name, **device.item.fields) }
        self.InterfacesAdded(device.path, spec)
    return devices

  def GetSpecs (self, things):
    # in_signature='', out_signature='a{oa{sa{sv}}}')
    specs = [ ]
    ifaces = dict( )
    paths = dict( )
    for thing in things:
      print thing.path
      print thing.OWN_IFACE
      print thing.item.fields
      spec = { thing.OWN_IFACE:  dict(name=thing.item.name, **thing.item.fields) }
      paths[thing.path] = spec
      specs.append([ thing.path,  spec  ])
    print "DBUS Managed SPEC", specs
    return paths
    return paths.keys( )
  def get_reports (self, announce=False):
    specs = [ ]
    for report in self.reports:
      print report.OWN_IFACE
      print report.item.fields
      spec = { report.OWN_IFACE: dict(name=report.item.name, **report.item.fields) }
      specs.append({ report.path: [ spec ] })
    print "REPORTS DBUS SPEC", specs
    return specs
  def lookup_reports (self, announce=False):
    reports = Reports.FromParent(self)
    for report in reports:
      if announce:
        print report.OWN_IFACE
        print report.item.fields
        spec = { report.OWN_IFACE: dict(name=report.item.name, **report.item.fields) }
        self.InterfacesAdded(report.path, spec)
    return reports


  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='', out_signature='s')
  def Version (self):
    print "Howdy!", openaps.__version__
    return openaps.__version__


class Configurable (GPropSync):
  # name = gobject.property(type=str, blurb="Name of thing")
  @gobject.Property(type=str, blurb="Name of thing")
  def name (self):
    return self.item.name
  PROP_SIGS = {
    'name': 's'
  }
  isExtra = False
  def __init__ (self, bus, path, device, IsExtra=False):
    # print self.__class__.Version
    self.item = device
    self.path = path
    GPropSync.__init__(self, bus, path)
    if device.fields:
      self.set_property('name', device.name)
      """
      for key in device.fields:
        self.set_property(key, device.fields[key])
      """
    self.name = device.name
    for field in self.item.required:
      self.PROP_SIGS[field] = self.PROP_SIGS.get(field, 's')
    fields = self.item.fields
    if self.isExtra:
      # print "EXTRA", self.path
      # print self.item.extra.fields
      fields = self.item.extra.fields
    for x in fields.keys( ):
      self.PROP_SIGS[x] = self.PROP_SIGS.get(x, 's')
    self.PropertiesChanged(self.OWN_IFACE, fields, [])
    if hasattr(self.item, 'extra') and not IsExtra:
      extra_path = self.path + 'Extra'
      self.extra_config = ExtraConfig(bus, extra_path, self.item, IsExtra=True)
   
  @classmethod
  def LookUp (Klass, parent, announce=False):
    reports = Klass.FromParent(parent)
    for report in reports:
      if announce:
        print report.OWN_IFACE
        print report.item.fields
        fields = report.item.fields
        if Klass.isExtra:
          fields = report.item.extra.fields
        spec = { report.OWN_IFACE: dict(name=report.item.name, **fields) }
        parent.InterfacesAdded(report.path, spec)
    return reports


  @classmethod
  def FromParent (Klass, parent):
    results = [ ]
    devices = Klass.GetMap(parent)
    for name in devices:
      device = devices[name]
      path = Klass.PATH_SPEC % (len(results))
      results.append(Klass(parent.bus, path, device))
    return results

  @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
  def Get(self, interface_name, property_name):
      if getattr(self, property_name, None):
        return getattr(self, property_name)
      fields = self.item.fields
      if self.isExtra:
        fields = self.item.extra.fields
      return fields[property_name]
  @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                       in_signature='s', out_signature='a{sv}')
  def GetAll(self, interface_name):
      if interface_name == dbus.PROPERTIES_IFACE:
        return { }
      if interface_name == self.OWN_IFACE:
          # props = dict([(prop.name.replace('-', '_'), getattr(self, prop.name.replace('-', '_'))) for prop in self.props])
          # return props
          fields = self.item.fields
          if self.isExtra:
            fields = self.item.extra.fields
          return dict(name=self.name, **fields)
      else:
          raise dbus.exceptions.DBusException(
              'com.example.UnknownInterface',
              'The Foo object does not implement the %s interface'
                  % interface_name)
  @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                       in_signature='ssv')
  def Set(self, interface_name, property_name, new_value):
      # validate the property name and value, update internal state
      if interface_name == self.OWN_IFACE:
        # self.set_property(property_name, new_value)
        fields = self.item.fields
        if self.isExtra:
          fields = self.item.extra.fields
        old_value = fields.get(property_name, None)
        old = [ ]
        if old_value is not None and old_value != new_value:
          old = [ { property_name: old_value } ]
        fields[property_name] = new_value
        self.PropertiesChanged(interface_name,
            { property_name: new_value }, old)


# obsoleted with entry_points

"""
class Reports (Configurable):
  OWN_IFACE = OPENAPS_IFACE + '.Report'
  PATH_SPEC = PATH + '/Instance/Report%s'

  @classmethod
  def GetMap (Klass, parent):
    devices = openaps.reports.get_report_map(parent.config)
    return devices

  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='', out_signature='s')
  def Version (self):
    print "Howdy!", openaps.__version__
    return openaps.__version__

class Alias (Configurable):
  OWN_IFACE = OPENAPS_IFACE + '.Alias'
  PATH_SPEC = PATH + '/Instance/Alias%s'

  @classmethod
  def GetMap (Klass, parent):
    devices = openaps.alias.get_alias_map(parent.config)
    return devices

  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='', out_signature='s')
  def Version (self):
    print "Howdy!", openaps.__version__
    return openaps.__version__


class Vendors (Configurable):
  OWN_IFACE = OPENAPS_IFACE + '.Vendor'
  PATH_SPEC = PATH + '/Instance/Vendor%s'

  @classmethod
  def GetMap (Klass, parent):
    devices = openaps.vendors.plugins.get_vendor_map(parent.config)
    return devices

  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='', out_signature='s')
  def Version (self):
    print "Howdy!", openaps.__version__
    return openaps.__version__

"""

class ExtraConfig (Configurable):
  OWN_IFACE = OPENAPS_IFACE + '.DeviceExtra'
  PATH_SPEC = PATH + '/Instance/Device%s'
  isExtra = True

  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='', out_signature='s')
  def Version (self):
    print "Howdy!", openaps.__version__
    return openaps.__version__

def configurable_entries ( ):
  import pkg_resources
  mods = { }
  for entry in pkg_resources.iter_entry_points('openaps.importable'):
    mod = entry.load( )
    mods[entry.name] = MakeManaged(mod, entry)
  return mods

def MakeManaged (mod, entry):
  title_name = entry.name.title( )
  iface_name = OPENAPS_IFACE + '.' + title_name
  title_item = mod.Exported.Configurable.prefix.title( )

  class ManagedObject (Configurable):
    __name__ = mod.Exported.Configurable.__name__
    OWN_IFACE = iface_name
    PATH_SPEC = PATH + '/Instance/' + title_item + '%s'
    core = mod
    entry_point = entry

    @classmethod
    def GetMap (Klass, parent):
      devices = mod.Exported.get_map(parent.config)
      return devices

    @dbus.service.method(dbus_interface=OWN_IFACE,
                         in_signature='', out_signature='s')
    def Version (self):
      print "Howdy!", openaps.__version__
      return openaps.__version__
    pass
  return ManagedObject
"""
class Devices (Configurable):
  OWN_IFACE = OPENAPS_IFACE + '.Device'
  PATH_SPEC = PATH + '/Instance/Device%s'
  PROP_SIGS = {
    'name': 's'
  , 'vendor': 's'
  , 'extra': 's'
  }

  @classmethod
  def GetMap (Klass, parent):
    devices = openaps.devices.get_device_map(parent.config)
    return devices

  @dbus.service.method(dbus_interface=OWN_IFACE,
                       in_signature='', out_signature='s')
  def Version (self):
    print "Howdy!", openaps.__version__
    return openaps.__version__

  @classmethod
  def FromConfig (Klass, config):
    devices =  openaps.devices.get_device_map(config)
    print "FOUND DEVICES", devices
    return devices
"""
