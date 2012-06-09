from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('django_mongodb_extras.views',
    # Examples:
    # url(r'^$', 'teslalc_ru.views.home', name='home'),
    #url(r'test$', TemplateView.as_view(template_name="test.html")),
    #url(r'test2$', TemplateView.as_view(template_name="test2.html")),

    url(r'ajax/get_admin_models_list$', "get_admin_models_list", name="django_mongodb_extras_ajax_get_admin_models_list"),
    url(r'ajax/get_embedded_admin_models_list$', "get_admin_models_list", name="django_mongodb_extras_ajax_get_embedded_admin_models_list",
    kwargs={"embedded": True}),
)
