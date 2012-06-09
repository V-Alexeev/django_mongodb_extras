from django.contrib.admin.views.decorators import staff_member_required
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import models

from annoying.decorators import ajax_request


@ajax_request
@staff_member_required
def get_admin_models_list(request, embedded=False):
    def has_admin(model):
        try:
            result = reverse('admin:%s_%s_%schange' % (
                model._meta.app_label,
                model._meta.module_name,
                ("embedded_" if embedded else ""),
                ), args='0')
        except NoReverseMatch:
            return False
        else:
            return result

    return {'result':[{
        'verbose_name': unicode(m._meta.verbose_name),
        'table_name': unicode(m._meta.db_table),
        'admin_url': has_admin(m).rstrip('/0')
    } for m in models.get_models() if has_admin(m)]}