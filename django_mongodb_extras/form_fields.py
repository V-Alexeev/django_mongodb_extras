from itertools import izip, cycle, count

from django.core import validators
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.forms import fields, widgets
from django.core.exceptions import ValidationError
from django.forms.util import ErrorList
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.db import models

from bson import ObjectId
from bson.dbref import DBRef
from bson.errors import InvalidId

from utils import dbref_to_model_instance

BSON_TYPES_CHOICES = {
    'int': ('int', "Integer"),
    'float': ('float', "Real"),
    'unicode': ('unicode', "String"),
    'DBRef': ('DBRef', "DBRef"),
    'datetime': ('datetime', "Date"),
    'EmbeddedModel': ('EmbeddedModel', 'Embed'),
}


class DynamicLengthMultiValueField(fields.MultiValueField):
    """
    A Field that aggregates the logic of multiple Fields, which can be repeated
    any number of times.

    Its clean() method takes a "decompressed" list of values, which are then
    cleaned into a single value according to self.fields. The fields that are
    given as fields argument are applied in the given order until the values
    list is exhausted. Once all fields are cleaned, the list of clean values is
    "compressed" into a single value.

    Subclasses should not have to implement clean(). Instead, they must
    implement compress(), which takes a list of valid values and returns a
    "compressed" version of those values -- a single value.

    You'll probably want to use this with DynamicLengthMultiWidget.
    """

    def clean(self, value):
        """
        Validates every value in the given list. A value is validated against
        the corresponding Field in self.fields.

        For example, if this MultiValueField was instantiated with
        fields=(DateField(), TimeField()), clean() would call
        DateField.clean(value[0]) and TimeField.clean(value[1]).
        """
        clean_data = []
        errors = ErrorList()
        if not value or isinstance(value, (list, tuple)):
            if not value or not [v for v in value if v not in validators.EMPTY_VALUES]:
                if self.required:
                    raise ValidationError(self.error_messages['required'])
                else:
                    return self.compress([])
        else:
            raise ValidationError(self.error_messages['invalid'])

        for field_value, field in izip(value, cycle(self.fields)):
            if self.required and field_value in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['required'])
            try:
                clean_data.append(field.clean(field_value))
            except ValidationError, e:
                # Collect all validation errors in a single list, which we'll
                # raise at the end of clean(), rather than raising a single
                # exception for the first error we encounter.
                errors.extend(e.messages)
        if errors:
            raise ValidationError(errors)

        out = self.compress(clean_data)
        self.validate(out)
        return out


class DynamicLengthMultiWidget(widgets.MultiWidget):
    """
    A MultiWidget with support for dynamically changing value length.

    Can load values of any length, and has JavaScript to allow
    client-side addition and deletion of values.
    """
    def render(self, name, value, attrs=None):
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
            # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        if len(value) < len(self.widgets): value = [None for x in range(len(self.widgets))] # We should at least show empty widgets
        for widget_value, widget, i in izip(value, cycle(self.widgets), count()):
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            output.append("<div>")
            output.append(widget.render(name + '_%s' % i, widget_value, final_attrs))
            output.append("<span class='vDynamicMultiWidgetDelete'><img src='%simg/admin/icon_deletelink.gif' alt='%s'></span></div>" % (settings.ADMIN_MEDIA_PREFIX, unicode(_("Delete"))))
        output.append("<span class='vDynamicMultiWidgetAdd'><img src='%simg/admin/icon_addlink.gif' alt='%s'></span>" % (settings.ADMIN_MEDIA_PREFIX, unicode(_("Add Another"))))
        output.append("<script type='text/javascript'>__all_models_query_link='%s'; __all_embedded_models_query_link='%s';</script>" %
                      (reverse("django_mongodb_extras_ajax_get_admin_models_list"), reverse("django_mongodb_extras_ajax_get_embedded_admin_models_list")))
        return mark_safe(self.format_output(output))

    def value_from_datadict(self, data, files, name):
        keystring = "|".join(data.keys())
        result = []
        for i, widget in izip(count(), cycle(self.widgets)):
            if "|%s_%s" % (name, i) in keystring:
                result.append(widget.value_from_datadict(data, files, name + '_%s' % i))
            else:
                break
        return result

    def _has_changed(self, initial, data):
        if initial is None:
            initial = [u'' for x in range(0, len(data))]
        else:
            if not isinstance(initial, list):
                initial = self.decompress(initial)
        for widget, initial, data in izip(cycle(self.widgets), initial, data):
            if widget._has_changed(initial, data):
                return True
        return False

    class Media:
        js = (settings.STATIC_URL + "js/dynamic_multi_widget.js",)


class ListFieldWidget(DynamicLengthMultiWidget):
    def __init__(self, allowed_type_choices=None, attrs=None):
        widgets = (TypedFieldWidget(allowed_type_choices=allowed_type_choices, attrs=attrs),)
        super(ListFieldWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value is None:
            return [None]
        return value


def _generate_embedded_links_javascript(change_link, name):
    pre_href = u"%s{__INSERT_PK_HERE}/%s/" % (change_link, name)
    pre_change_link = u'<a href="{__INSERT_LINK_HERE}"> <img src="/static/admin/img/admin/selector-search.gif" width="16" height="16" alt="%s" /></a>' % (_("Search"))
    pre_delete_link = u'<a href="{__INSERT_LINK_HERE}delete/"> <img src="/static/admin/img/admin/icon_deletelink.gif" alt="%s" /></a>' % (_("Delete"))
    script = u"""
        <script type='text/javascript'>
        var link = "";
        if (window.location.href.search(/\/[^\/]+\/[^\/]+\/embedded\/[^\/]+\/[^\/]+\//) > -1) {
            link = window.location.href + '%s' + '/';
        } else {
            var object_id = window.location.href.match(/\/([^\/]+)\/$/)[1];
            link = '%s'.replace('{__INSERT_PK_HERE}', object_id);
        }

        document.write('%s'.replace('{__INSERT_LINK_HERE}', link));
        document.write('%s'.replace('{__INSERT_LINK_HERE}', link));
        </script>
        """ % (name, pre_href, pre_change_link, pre_delete_link)
    return script



class TypedFieldWidget(widgets.MultiWidget):
    """
    A Widget that allows to enter a field's value and to select
    its type out of types supported by BSON
    """
    def __init__(self, allowed_type_choices=None, attrs=None, widgets_=None):
        if attrs is None: attrs = {}
        if widgets_ is None:
            widgets_ = (widgets.Select(choices=allowed_type_choices or BSON_TYPES_CHOICES.values()),
                   widgets.HiddenInput(), # Used to select table for DBRef, If needed, will be changed to <select> by javascript
                   widgets.TextInput())
        attrs.update({'class': 'vTypedField'})
        super(TypedFieldWidget, self).__init__(widgets_, attrs)

    def decompress(self, value):
        if  isinstance(value, models.Model): # An embedded model here!
            return ['EmbeddedModel', type(value)._meta.db_table, unicode(value)]
        elif isinstance(value, DBRef):
            return ['DBRef', value.collection, unicode(value.id)]
        elif value:
            return [type(value).__name__, None, value]
        return [None, None, None]

    def render(self, name, value, attrs=None):
        if isinstance(value, models.Model):
            self.widgets[2].attrs.update({'disabled': 'disabled'}) # Disable input for EmbeddedModel
        result = super(TypedFieldWidget, self).render(name, value, attrs)
        if isinstance(value, DBRef) or isinstance(value, models.Model):
            try:
                obj = dbref_to_model_instance(value) if isinstance(value,DBRef) else value
            except ObjectDoesNotExist:
                result += '<strong class="vTypedField" style="color:red;">[Object not found]</strong>'
            else:
                result += '<strong class="vTypedField">%s</strong>' % unicode(obj)

        return mark_safe(result)

    class Media:
        js = (settings.STATIC_URL + "js/typed_field_widget.js",
              settings.ADMIN_MEDIA_PREFIX + "js/admin/RelatedObjectLookups.js")



class HiddenTypedFieldWidget(TypedFieldWidget):
    """
    A hidden TypedFieldWidget
    """
    is_hidden = True

    def __init__(self, attrs=None):
        widgets_ = (widgets.HiddenInput(),
                    widgets.HiddenInput(),
                    widgets.HiddenInput())
        super(HiddenTypedFieldWidget, self).__init__(attrs, widgets_)


class DBRefField(fields.Field):
    """A field type used to clean DBRefs"""
    default_error_messages = {
        'invalid': _(u"Can't dereference this DBRef."),
        }

    def to_python(self, value):
        if len(value) != 2: # We should have [collection, _id]
            return None
        dbref = DBRef(*value)
        from django.db import connection
        if connection.database.dereference(dbref) is None:
            try:
                dbref = DBRef(value[0], ObjectId(value[1])) # Maybe it's an ObjectId?
            except InvalidId:
                pass
            if connection.database.dereference(dbref) is None:
                raise ValidationError(self.error_messages['invalid'])
        return dbref


class EmbeddedModelWidget(widgets.Input):
    def __init__(self, attrs=None, change_link=None):
        self.change_link = change_link
        if attrs is None: attrs = {}
        attrs.update({'disabled':'disabled'})
        super(EmbeddedModelWidget, self).__init__(attrs=attrs)

    def render(self, name, value, attrs=None):
        result =  super(EmbeddedModelWidget, self).render(name, value, attrs)
        result += _generate_embedded_links_javascript(self.change_link, name)
        return mark_safe(result)


class EmbeddedModelField(fields.Field):
    def __init__(self, model=None, embedded_model=None, *args, **kwargs):
        if kwargs.get('widget', EmbeddedModelWidget) is EmbeddedModelWidget:
            change_link = reverse('admin:%s_%s_embedded_change' % (
                embedded_model._meta.app_label,
                embedded_model._meta.module_name
                ), args=(
                '/'.join([   model._meta.app_label,
                             model._meta.module_name,
                             ]),
                ))
            widget = EmbeddedModelWidget(change_link=change_link)
            kwargs.update({'widget': widget})

        fields.Field.__init__(self, *args, **kwargs)


class TypedField(fields.MultiValueField):
    widget = TypedFieldWidget
    hidden_widget = HiddenTypedFieldWidget
    default_error_messages = {
        'invalid_type': _(u'Are you trying to use an incorrect type?'),
        }

    def __init__(self, allowed_type_choices=None, *args, **kwargs):
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])
        fields_ = (
            fields.ChoiceField(choices=allowed_type_choices or BSON_TYPES_CHOICES.values()),
            fields.CharField(max_length=10000),
            fields.CharField(max_length=10000))
        if kwargs.get('widget', TypedFieldWidget) is TypedFieldWidget:
            widget = TypedFieldWidget(allowed_type_choices=allowed_type_choices)
            kwargs.update({'widget': widget})
        super(TypedField, self).__init__(fields_, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            if data_list[2] in validators.EMPTY_VALUES:
                return None
            elif data_list[0] == "DBRef":
                cleaner = DBRefField()
                return cleaner.clean(data_list[1:3])
            elif data_list[0] == "int":
                cleaner = fields.IntegerField()
            elif data_list[0] == "float":
                cleaner = fields.FloatField()
            elif data_list[0] == "unicode":
                cleaner = fields.CharField(max_length=10000)
            elif  data_list[0] == "datetime":
                cleaner = fields.DateTimeField()
            else:
                raise ValidationError(self.error_messages['invalid_type'])
            return cleaner.clean(data_list[2])
        return None


class ListField(DynamicLengthMultiValueField):
    widget = ListFieldWidget
    clean_takes_initial = True

    def __init__(self, allowed_type_choices=None, *args, **kwargs):
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])
        fields = (
            TypedField(allowed_type_choices=allowed_type_choices),
            )
        if kwargs.get('widget', ListFieldWidget) is ListFieldWidget:
            widget = ListFieldWidget(allowed_type_choices=allowed_type_choices)
            kwargs.update({'widget': widget})
        super(ListField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        return [data for data in data_list if data is not None]

    def clean(self, value, initial=None):
        """
        We should make sure not to modify EmbeddedModels.

        Initial should be provided by a patch to django/forms/forms.py.
        """
        result = super(ListField, self).clean(value)
        if callable(initial): initial = initial() # Sometimes we somehow have a lambda here
        if initial is not None:
            for i in range(len(value)):
                if i + 1 > len(initial):
                    break
                if value[i][0] == u"EmbeddedModel":
                    result.insert(i, initial[i])
        return result