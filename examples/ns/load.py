"""deserialization tools"""
import typing as t
from datetime import datetime
from functools import partial

from toolz import compose, flip, valmap
from valuable import load, xml

from . import types

registry = load.PrimitiveRegistry({
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
}) | load.GenericRegistry({
    t.List: load.list_loader,
}) | load.get_optional_loader | load.DataclassRegistry({
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
        'status':            'Status',
    }), **{
        'components':        xml.elemsgetter('ReisDeel'),
        'notifications':     xml.elemsgetter('Melding'),
    }, **{
        'optimal':           xml.textgetter('Optimaal', default='false')
    }},
    types.Departure: {**valmap(xml.textgetter, {
        'ride_number':      'RitNummer',
        'time':             'VertrekTijd',
        'destination':      'EindBestemming',
        'train_type':       'TreinSoort',
        'carrier':          'Vervoerder',
        'platform':         'VertrekSpoor',
    }), **{
        'platform_changed': xml.attribgetter('VertrekSpoor', 'wijziging'),
        'comments':         xml.textsgetter('Opmerkingen/Opmerking'),
        'delay':            xml.textgetter('VertrekVertragingTekst',
                                           default=None),
        'travel_tip':       xml.textgetter('ReisTip', default=None),
        'route_text':       xml.textgetter('RouteTekst', default=None),
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
    types.Journey.Component.Stop: {
        'name':             xml.textgetter('Naam'),
        'time':             compose(lambda x: x or None,
                                    xml.textgetter('Tijd')),
        'platform_changed': xml.attribgetter('Spoor', 'wijziging',
                                             default=None),
        'delay':            xml.textgetter('VertrekVertraging', default=None),
        'platform':         xml.textgetter('Spoor', default=None)
    },
    types.Journey.Notification: valmap(xml.textgetter, {
        'id':      'Id',
        'serious': 'Ernstig',
        'text':    'Text',
    })
})
