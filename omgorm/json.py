"""classes and utilities for dealing with JSON API data"""
from . import core


class Field(core.Field):

    def get_value(self, instance):
        return instance.api_obj[self.name]
