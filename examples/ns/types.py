"""datastructures and type definitions"""
import enum
import typing as t
from datetime import datetime
from functools import partial
from operator import attrgetter

from dataclasses import dataclass

dclass = partial(dataclass, frozen=True, repr=False)


@dclass()
class Station:
    name:       str
    full_name:  str
    short_name: str
    code:       str
    type:       str
    country:    str
    uic:        str
    lat:        float
    lon:        float
    synonyms:   t.List[str]

    latlon = property(attrgetter('lat', 'lon'))

    def __repr__(self):
        country_suffix = f' ({self.country})' if self.country != 'NL' else ''
        return f'<Station: {self.full_name + country_suffix}>'


@dclass()
class Departure:
    """a train departure"""
    ride_number:      int
    time:             datetime
    delay:            t.Optional[str]
    destination:      str
    train_type:       str
    route_text:       t.Optional[str]
    carrier:          str
    platform:         str
    platform_changed: bool
    travel_tip:       t.Optional[str]
    comments:         t.List[str]

    def __repr__(self):
        delaytext = f'[{self.delay}]' if self.delay else ''
        platform = f'{self.platform}{"*" if self.platform_changed else ""}'
        alert = ' (!)' if self.comments or self.travel_tip else ''
        text = (f'{self.time:%H:%M}{delaytext} | {self.destination} '
                f'| {platform}{alert}')
        return f'<Departure: {text}>'


@dclass()
class Journey:
    """a journey option"""

    @dclass()
    class Component:
        """a journey option component"""

        class Status(enum.Enum):
            """status of a journey component"""
            ON_SCHEDULE = 'VOLGENS-PLAN'
            CHANGED = 'GEWIJZIGD'
            CANCELLED = 'GEANNULEERD'
            TRANSFER_NOT_POSSIBLE = 'OVERSTAP-NIET-MOGELIJK'
            DELAYED = 'VERTRAAGD'
            NEW = 'NIEUW'

            def __repr__(self):
                return f'Status.{self.name}'

        @dclass()
        class Stop:
            """a travel stop on a journey component"""
            name:             str
            time:             t.Optional[datetime]
            delay:            t.Optional[str]
            platform:         t.Optional[str]
            platform_changed: t.Optional[bool]

            def __repr__(self):
                time = f'{self.time:%H:%M}' if self.time else '??:??'
                delay_text = f'[{self.delay}]' if self.delay else ''
                platform_changed = ' (changed)' if self.platform_changed else''
                platform_text = (f'| platform {self.platform}'
                                 if self.platform else '')
                text = (f'{self.name} | {time} {delay_text}'
                        f'{platform_text}{platform_changed}')
                return f'<Stop: {text}>'

        kind:        str
        carrier:     str
        type:        str
        ride_number: int
        status:      Status
        details:     t.List[str]
        stops:       t.List[Stop]

        def __repr__(self):
            status_suffix = (f' [{self.status.name}]'
                             if self.status is not self.Status.ON_SCHEDULE
                             else '')
            text = f'({self.carrier}) {self.type}' + status_suffix
            return f'<Component: {text}>'

    @dclass()
    class Notification:
        """an notification about a journey option"""
        id:      t.Optional[str]
        serious: bool
        text:    str

        def __repr__(self):
            text = self.text.upper() if self.serious else self.text
            return f'<Notification: {text}>'

    class Status(enum.Enum):
        """status of a journey option"""
        ON_SCHEDULE = 'VOLGENS-PLAN'
        CHANGED = 'GEWIJZIGD'
        DELAYED = 'VERTRAAGD'
        NEW = 'NIEUW'
        NOT_OPTIMAL = 'NIET-OPTIMAAL'
        NOT_POSSIBLE = 'NIET-MOGELIJK'
        PLAN_CHANGED = 'PLAN-GEWIJZGD'

        def __repr__(self):
            return f'Status.{self.name}'

    transfer_count:    int
    planned_duration:  str
    planned_departure: datetime
    planned_arrival:   datetime
    actual_duration:   str
    actual_departure:  datetime
    actual_arrival:    datetime
    optimal:           bool
    components:        t.List[Component]
    notifications:     t.Optional[t.List[Notification]]
    status:            Status

    def __repr__(self):
        text = (f'{self.actual_departure:%H:%M} -> {self.actual_arrival:%H:%M}'
                f' | {self.actual_duration} | {self.transfer_count}'
                + (' (!)' if self.notifications else ''))
        return f'<Journey: {text}>'
