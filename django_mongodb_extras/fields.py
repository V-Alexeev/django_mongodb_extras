from django.db import models

from djangotoolbox import fields

import form_fields


class ListField(fields.ListField):
    def formfield(self, **kwargs):
        if isinstance(self.item_field, fields.EmbeddedModelField):
            allowed_type_choices = (form_fields.BSON_TYPES_CHOICES['EmbeddedModel'],)
        elif isinstance(self.item_field, models.IntegerField):
            allowed_type_choices = (form_fields.BSON_TYPES_CHOICES['int'],)
        elif isinstance(self.item_field, models.FloatField):
            allowed_type_choices = (form_fields.BSON_TYPES_CHOICES['float'],)
        elif isinstance(self.item_field, models.CharField):
            allowed_type_choices = (form_fields.BSON_TYPES_CHOICES['unicode'],)
        elif isinstance(self.item_field, models.DateTimeField):
            allowed_type_choices = (form_fields.BSON_TYPES_CHOICES['datetime'],)
        elif isinstance(self.item_field, fields.RawField):
            allowed_type_choices = form_fields.BSON_TYPES_CHOICES.copy()
            allowed_type_choices.pop('EmbeddedModel')
            allowed_type_choices = allowed_type_choices.values()
        else:
            allowed_type_choices = form_fields.BSON_TYPES_CHOICES
        defaults = {'form_class': form_fields.ListField, 'widget': form_fields.ListFieldWidget,
                    'allowed_type_choices': allowed_type_choices}
        defaults.update(kwargs)
        return super(fields.AbstractIterableField, self).formfield(**defaults)


class EmbeddedModelField(fields.EmbeddedModelField):
    def formfield(self, **kwargs):
        defaults = {'form_class': form_fields.EmbeddedModelField, 'widget': form_fields.EmbeddedModelWidget,
                    'embedded_model': self.embedded_model, 'model': self.model}
        defaults.update(kwargs)
        return super(EmbeddedModelField, self).formfield(**defaults)