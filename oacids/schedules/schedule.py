
from openaps.configurable import Configurable

import recurrent


class Schedule (Configurable):
  prefix = 'schedule'
  required = [ 'phases', 'rrule' ]
  url_template = "schedule://{name:s}/{rrule:s}"

  @classmethod
  def parse_rrule (Klass, rrule):
    parser = recurrent.RecurringEvent( )
    rule = parser.parse(rrule)
    return rule

