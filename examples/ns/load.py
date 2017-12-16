import typing as t
from datetime import datetime
from functools import partial

import snug
from snug.utils import compose, flip, valmap

from . import types

xml = snug.xml


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
    types.Station: {**valmap(xml.textgetter, {
        'code':       'Code',
        'type':       'Type',
        'country':    'Land',
        'uic':        'UICCode',
        'lat':        'Lat',
        'lon':        'Lon',
        'name':       'Namen/Middel',
        'full_name':  'Namen/Lang',
        'short_name': 'Namen/Kort',
    }), **{
        'synonyms':   xml.textsgetter('Synoniemen/Synoniem'),
    }},
    types.Journey: {**valmap(xml.textgetter, {
        'transfer_count':    'AantalOverstappen',
        'planned_duration':  'GeplandeReisTijd',
        'planned_departure': 'GeplandeVertrekTijd',
        'planned_arrival':   'GeplandeAankomstTijd',
        'actual_duration':   'ActueleReisTijd',
        'actual_departure':  'ActueleVertrekTijd',
        'actual_arrival':    'ActueleAankomstTijd',
        'optimal':           'Optimaal',
        'status':            'Status',
    }), **{
        'components':        xml.elemsgetter('ReisDeel'),
        'notifications':     xml.elemsgetter('Melding'),
    }},
    types.Departure: {**valmap(xml.textgetter, {
        'ride_number':      'RitNummer',
        'time':             'VertrekTijd',
        'delay':            'VertrekVertragingTekst',
        'destination':      'EindBestemming',
        'train_type':       'TreinSoort',
        'route_text':       'RouteTekst',
        'carrier':          'Vervoerder',
        'platform':         'VertrekSpoor',
        'travel_tip':       'ReisTip',
    }), **{
        'platform_changed': xml.attribgetter('VertrekSpoor', 'wijziging'),
        'comments':         xml.textsgetter('Opmerkingen/Opmerking'),
    }},
    types.Journey.Component: {**valmap(xml.textgetter, {
        'carrier':     'Vervoerder',
        'type':        'VervoerType',
        'ride_number': 'RitNummer',
        'status':      'Status',
    }), **{
        'details':     xml.textsgetter('Reisdetails/Reisdetail'),
        'kind':        xml.attribgetter('.', 'reisSoort'),
        'stops':       xml.elemsgetter('ReisStop'),
    }},
    types.Journey.Component.Stop: {**valmap(xml.textgetter, {
        'name':             'Naam',
        'delay':            'VertrekVertraging',
        'platform':         'Spoor',
    }), **{
        'time':             compose(lambda x: x or None,
                                    xml.textgetter('Tijd')),
        'platform_changed': xml.attribgetter('Spoor', 'wijziging'),
    }},
    types.Journey.Notification: valmap(xml.textgetter, {
        'id':      'Id',
        'serious': 'Ernstig',
        'text':    'Text',
    })
})
