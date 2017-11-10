import typing as t
from datetime import datetime
from toolz.curried import partial, flip

import snug

from . import types


registry = snug.load.PrimitiveRegistry({
    bool:     dict(true=True, false=False).__getitem__,
    datetime: partial(flip(datetime.strptime), '%Y-%m-%dT%H:%M:%S%z'),
    str:      str.strip,
    **{
        c: c for c in [
            int,
            float,
            types.Journey.Status,
            types.Journey.Component.Status
        ]
    }
}) | snug.load.GenericRegistry({
    t.List: snug.load.list_loader,
}) | snug.load.get_optional_loader | snug.load.DataclassRegistry({
    types.Station: {
        'code':       'Code/text()',
        'type':       'Type/text()',
        'country':    'Land/text()',
        'uic':        'UICCode/text()',
        'lat':        'Lat/text()',
        'lon':        'Lon/text()',
        'name':       'Namen/Middel/text()',
        'full_name':  'Namen/Lang/text()',
        'short_name': 'Namen/Kort/text()',
        'synonyms':   'Synoniemen/Synoniem/text()',
    },
    types.Journey: {
        'transfer_count':    'AantalOverstappen/text()',
        'planned_duration':  'GeplandeReisTijd/text()',
        'planned_departure': 'GeplandeVertrekTijd/text()',
        'planned_arrival':   'GeplandeAankomstTijd/text()',
        'actual_duration':   'ActueleReisTijd/text()',
        'actual_departure':  'ActueleVertrekTijd/text()',
        'actual_arrival':    'ActueleAankomstTijd/text()',
        'optimal':           'Optimaal/text()',
        'components':        'ReisDeel',
        'notifications':     'Melding',
        'status':            'Status/text()',
    },
    types.Departure: {
        'ride_number':      'RitNummer/text()',
        'time':             'VertrekTijd/text()',
        'delay':            'VertrekVertragingTekst/text()',
        'destination':      'EindBestemming/text()',
        'train_type':       'TreinSoort/text()',
        'route_text':       'RouteTekst/text()',
        'carrier':          'Vervoerder/text()',
        'platform':         'VertrekSpoor/text()',
        'platform_changed': 'VertrekSpoor/@wijziging',
        'travel_tip':       'ReisTip/text()',
        'comments':         'Opmerkingen/Opmerking/text()',
    },
    types.Journey.Component: {
        'kind':        '@reisSoort',
        'carrier':     'Vervoerder/text()',
        'type':        'VervoerType/text()',
        'ride_number': 'RitNummer/text()',
        'status':      'Status/text()',
        'details':     'Reisdetails.Reisdetail/text()',
        'stops':       'ReisStop',
    },
    types.Journey.Component.Stop: {
        'name':             'Naam/text()',
        'time':             'Tijd/text()',
        'delay':            'VertrekVertraging/text()',
        'platform':         'Spoor/text()',
        'platform_changed': 'Spoor/@wijziging',
    },
    types.Journey.Notification: {
        'id':      'Id/text()',
        'serious': 'Ernstig/text()',
        'text':    'Text/text()',
    }
})
