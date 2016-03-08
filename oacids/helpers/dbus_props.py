from gi.repository import GObject as gobject
import dbus.service
from dbus.gi_service import ExportedGObject

import _dbus_bindings

from dbus import validate_interface_name
import inspect

INTROSPECTABLE_IFACE=dbus.INTROSPECTABLE_IFACE
ObjectManager = 'org.freedesktop.DBus.ObjectManager'
class WithProperties (ExportedGObject):
  
    def _reflect_on_property(cls, func):
        args = func._dbus_args

        if func._dbus_type_signature:
            # convert signature into a tuple so length refers to number of
            # types, not number of characters. the length is checked by
            # the decorator to make sure it matches the length of args.
            type_sig = tuple(Signature(func._dbus_type_signature))
        else:
            # magic iterator which returns as many v's as we need
            type_sig = _VariantSignature()

        access = None
        if func._dbus_access:
            access = func._dbus_access
            out_sig = Signature(func._dbus_out_signature)
        else:
            # its tempting to default to Signature('v'), but
            # for methods that return nothing, providing incorrect
            # introspection data is worse than providing none at all
            out_sig = []

        reflection_data = '    <property name="%s" type="%s" access="%s">\n' % (func.__name__, type_sig, access)
        for annotation in getattr(func, '_dbus_annotations', [ ]):
            reflection_data += '      <annotation name="%s" value="true" />\n' % pair
            # reflection_data += '      <arg direction="in"  type="%s" name="%s" />\n' % pair

        reflection_data += '    </property>\n'

        return reflection_data


    def _reflect_on_gproperty(cls, prop):
        gname = prop.name.replace('-', '_')
        type_sig = cls.PROP_SIGS.get(gname, 'v')
        access_map = {
          gobject.PARAM_READWRITE: 'readwrite'
        , gobject.PARAM_READABLE: 'read'
        , gobject.PARAM_WRITABLE: 'write'
        }
        access = 'read'
        if getattr(cls.__class__, gname, None):
          access = access_map.get(getattr(cls.__class__, gname).flags, 'read')
        reflection_data = '    <property name="%s" type="%s" access="%s">\n' % (gname, type_sig, access)
        for annotation in getattr(prop, '_dbus_annotations', [ ]):
            reflection_data += '      <annotation name="%s" value="true" />\n' % pair
            # reflection_data += '      <arg direction="in"  type="%s" name="%s" />\n' % pair

        reflection_data += '    </property>\n'

        return reflection_data


    def _reflect_on_dict(cls, props):
        reflection_data = ''
        for name, prop in props.items( ):
          value = prop
          type_sig = cls.PROP_SIGS.get(name, 'v')
          access_map = {
            gobject.PARAM_READWRITE: 'readwrite'
          , gobject.PARAM_READABLE: 'read'
          , gobject.PARAM_WRITABLE: 'write'
          }
          access = 'readwrite'
          reflection_data += '    <property name="%s" type="%s" access="%s">\n' % (name, type_sig, access)
          for annotation in getattr(prop, '_dbus_annotations', [ ]):
              reflection_data += '      <annotation name="%s" value="true" />\n' % pair
              # reflection_data += '      <arg direction="in"  type="%s" name="%s" />\n' % pair

          reflection_data += '    </property>\n'

        return reflection_data
    @dbus.service.method(INTROSPECTABLE_IFACE, in_signature='', out_signature='s',
            path_keyword='object_path', connection_keyword='connection')
    def Introspect(self, object_path, connection):
        """Return a string of XML encoding this object's supported interfaces,
        methods and signals.
        """
        reflection_data = _dbus_bindings.DBUS_INTROSPECT_1_0_XML_DOCTYPE_DECL_NODE
        reflection_data += '<node name="%s">\n' % object_path

        interfaces = self._dbus_class_table[self.__class__.__module__ + '.' + self.__class__.__name__]
        for (name, funcs) in interfaces.items():
            reflection_data += '  <interface name="%s">\n' % (name)

            if name == self.OWN_IFACE:
              if getattr(getattr(self, 'item', None), 'fields', None):
                fields = self.item.fields
                if self.isExtra and hasattr(self.item, 'extra'):
                  fields = self.item.extra.fields
                reflection_data += self._reflect_on_dict(fields)
              for prop in self.props:
                reflection_data += self._reflect_on_gproperty(prop)

            for func in funcs.values():
                if getattr(func, '_dbus_is_method', False):
                    reflection_data += self.__class__._reflect_on_method(func)
                elif getattr(func, '_dbus_is_signal', False):
                    reflection_data += self.__class__._reflect_on_signal(func)
                elif getattr(func, '_dbus_is_property', False):
                    reflection_data += self.__class__._reflect_on_property(func)


            reflection_data += '  </interface>\n'

        for name in connection.list_exported_child_objects(object_path):
            reflection_data += '  <node name="%s"/>\n' % name

        reflection_data += '</node>\n'

        return reflection_data

class GPropSync (WithProperties):
    PROP_SIGS = { }
    def __init__ (self, bus=None, path=None):
        self.bus = bus or dbus.SessionBus( )
        ExportedGObject.__init__(self, self.bus.get_connection( ), path)
        self.sync_all_props( )
    def sync_all_props (self):
      for prop in self.props:
        self.connect("notify::%s" % prop.name, self.on_prop_change)
    def on_prop_change (self, obj, gparam):
      changed = {gparam.name.replace('-', '_'): getattr(self, gparam.name.replace('-', '_'))}
      # print changed
      self.PropertiesChanged(self.OWN_IFACE, changed, {})

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        return self.GetAll(interface_name).get(str(property_name), None)

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if interface_name in [ dbus.PROPERTIES_IFACE, dbus.INTROSPECTABLE_IFACE, ObjectManager ]:
          return { }
        if interface_name == self.OWN_IFACE:
            props = dict([(prop.name.replace('-', '_'), getattr(self, prop.name.replace('-', '_'))) for prop in self.props])
            return props
        else:
            raise dbus.exceptions.DBusException(
                'com.example.UnknownInterface',
                'The %s object does not implement the %s interface'
                    % (self.__class__.__name__, interface_name))

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ssv')
    def Set(self, interface_name, property_name, new_value):
        # validate the property name and value, update internal state
        if interface_name == self.OWN_IFACE:
          self.set_property(property_name, new_value)
        # self.PropertiesChanged(interface_name,
            # { property_name: new_value }, [])

    @dbus.service.signal(dbus_interface=dbus.PROPERTIES_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        pass

# class Timer(dbus.service.Object):
# class Timer(ExportedGObject):
class Manager (WithProperties):
    OWN_IFACE = None
    # ObjectManager
    schedules = [ ]
    def __init__ (self, path, bus=None):
      # self.__dbus_object_path__ = path
      self.bus = bus or dbus.SessionBus( )
      WithProperties.__init__(self, self.bus.get_connection( ), path)

    @dbus.service.method(dbus_interface=ObjectManager,
                         in_signature='', out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
      return self.get_all_managed( )
      return [ ]
    @dbus.service.signal(dbus_interface=ObjectManager,
                         signature='oa{sa{sv}}')
    def InterfacesAdded (self, path, iface_spec):
      pass
    @dbus.service.signal(dbus_interface=ObjectManager,
                         signature='oas')
    def InterfacesRemoved (self, path, iface_spec):
      pass
