
from openaps.configurable import Configurable

class Trigger (Configurable):
  prefix = 'trigger'
  required = [ 'then', ]
  url_template = "trigger://{name:s}/{then:s}"

