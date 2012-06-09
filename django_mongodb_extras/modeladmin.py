from bson.errors import InvalidId
from django import template
from django.contrib.admin.options import ModelAdmin, csrf_protect_m
from django.contrib.admin.util import unquote
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.utils.encoding import force_unicode
from django.utils.functional import update_wrapper
from django.db.models import get_model
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
from django.db import router, models



class EmbeddedAdmin(ModelAdmin):
    is_hidden = True # Will not show in admin indices

    errors = {
        'not_yet_saved': _("You are probably trying to access an embedded field of a model not yet saved.")
    }

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name

        urlpatterns = patterns('',
            url(r'^embedded/(.+)/delete/$',
                wrap(self.delete_view),
                name='%s_%s_embedded_delete' % info),
            url(r'^embedded/(.+)/$',
                wrap(self.change_view),
                name='%s_%s_embedded_change' % info),
        )
        return urlpatterns

    def get_object(self, request, object_id):
        def get_next_object(previous_object, field_name):
            try:
                field_name_as_int = int(field_name)
            except ValueError: # It's not an int, must be an attribute name
                return getattr(previous_object, field_name)
            else: # It's an int, must be an index
                return previous_object[field_name_as_int]

        app_name, model_name, object_id, field_names = object_id.split('/', 3)
        field_names = field_names.split('/')
        model = get_model(app_name, model_name)
        try:
            self.object_being_changed = model.objects.get(pk=object_id)
        except InvalidId:
            raise Http404(unicode(self.errors['not_yet_saved']))
        result = self.object_being_changed
        if field_names[-1].isdigit():
            for field_name in field_names[:-2]:
                result = get_next_object(result, field_name)
            self.embedded_model_being_changed = result
            self.parent_object = get_next_object(result, field_names[-2])
            self.index_in_parent_object = int(field_names[-1])
            self.embedded_field_being_changed = field_names[-2]
        else:
            for field_name in field_names[:-1]:
                result = get_next_object(result, field_name)
            self.embedded_model_being_changed = self.parent_object = result
            self.embedded_field_being_changed = field_names[-1]
            self.index_in_parent_object = None

        try:
            result = get_next_object(self.parent_object, field_names[-1])
        except AttributeError:
            raise Http404(unicode(self.errors['not_yet_saved']))
        except IndexError: # We have a ListField or something else which is indexable
            result = None # It's OK, we'll just extend the field when saving
        if result is None or\
        (not isinstance(result, models.Model) and self.index_in_parent_object is not None): # It wasn't an EmbeddedModelField until now
            result = self.model()
        self.path_to_field = field_names
        return result

    def delete_model(self, request, obj):
        if self.index_in_parent_object is None:
            setattr(self.parent_object, self.embedded_field_being_changed, None)
        else:
            del self.parent_object[self.index_in_parent_object]
        self.object_being_changed.save()

    def save_model(self, request, obj, form, change):
        if self.index_in_parent_object is None:
            setattr(self.parent_object, self.embedded_field_being_changed, obj)
        else:
            self.parent_object.extend([None for x in range((self.index_in_parent_object + 1) - len(self.parent_object))])
            self.parent_object[self.index_in_parent_object] = obj
            print self.object_being_changed
        self.object_being_changed.save()

    def response_change(self, request, obj):
        """
        Determines the HttpResponse for the change_view stage.
        """
        opts = obj._meta

        # Handle proxy models automatically created by .only() or .defer()
        verbose_name = opts.verbose_name
        if obj._deferred:
            opts_ = opts.proxy_for_model._meta
            verbose_name = opts_.verbose_name

        pk_value = obj._get_pk_val()

        msg = _('The %(name)s "%(obj)s" was changed successfully.') % {'name': force_unicode(verbose_name), 'obj': force_unicode(obj)}
        if "_continue" in request.POST:
            self.message_user(request, msg + ' ' + unicode(_("You may edit it again below.")))
            if "_popup" in request.REQUEST:
                return HttpResponseRedirect(request.path + "?_popup=1")
            else:
                return HttpResponseRedirect(request.path)
        else:
            self.message_user(request, msg)
            # Figure out where to redirect. We either redirect to
            # the parent embedded field change page or to the
            # parent object change page
            if len(self.path_to_field) > 2 or \
            (len(self.path_to_field) > 1 and self.index_in_parent_object is None):
                model_type = self.embedded_model_being_changed._meta.get_field(self.embedded_field_being_changed).model
                new_path_to_field = self.path_to_field[:-2] if self.index_in_parent_object is not None else self.path_to_field[:-1]
                return HttpResponseRedirect(reverse('admin:%s_%s_embedded_change' % (
                    model_type._meta.app_label,
                    model_type._meta.module_name
                ), args=(
                    '/'.join([
                        self.object_being_changed._meta.app_label,
                        self.object_being_changed._meta.module_name,
                        self.object_being_changed.pk,
                    ]+new_path_to_field),
                )))
            else:
                return HttpResponseRedirect(reverse('admin:%s_%s_change' % (
                    self.object_being_changed._meta.app_label,
                    self.object_being_changed._meta.module_name,
                ),
                    args=(self.object_being_changed.pk,)))


    @csrf_protect_m
    def delete_view(self, request, object_id, extra_context=None):
        "The 'delete' admin view for this model."
        opts = self.model._meta
        app_label = opts.app_label

        obj = self.get_object(request, unquote(object_id))

        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})

        using = router.db_for_write(self.model)

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.
        (deleted_objects, perms_needed, protected) = ({}, None, None)

        if request.POST: # The user has already confirmed the deletion.
            if perms_needed:
                raise PermissionDenied
            obj_display = force_unicode(obj)
            self.log_deletion(request, obj, obj_display)
            self.delete_model(request, obj)

            self.message_user(request, _('The %(name)s "%(obj)s" was deleted successfully.') % {'name': force_unicode(opts.verbose_name), 'obj': force_unicode(obj_display)})

            return self.response_change(request, obj)

        object_name = force_unicode(opts.verbose_name)

        if perms_needed or protected:
            title = _("Cannot delete %(name)s") % {"name": object_name}
        else:
            title = _("Are you sure?")

        context = {
            "title": title,
            "object_name": object_name,
            "object": obj,
            "deleted_objects": deleted_objects,
            "perms_lacking": perms_needed,
            "protected": protected,
            "opts": opts,
            "root_path": self.admin_site.root_path,
            "app_label": app_label,
            }
        context.update(extra_context or {})
        context_instance = template.RequestContext(request, current_app=self.admin_site.name)
        return render_to_response(self.delete_confirmation_template or [
            "admin/%s/%s/delete_confirmation.html" % (app_label, opts.object_name.lower()),
            "admin/%s/delete_confirmation.html" % app_label,
            "admin/delete_confirmation.html"
        ], context, context_instance=context_instance)