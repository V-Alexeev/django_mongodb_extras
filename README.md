###  Disclaimer

This app can by no means be regarded as finished, it’s more of alpha
quality. Its code can be quite shitty sometimes and it certainly doesn’t
yet support everything I would like it to support. But since right now
it doesn’t look like I will be finishing it in foreseeable future, and
since I don’t know of any other project offering at least this level of
functionality, I’ve decided to release it as is. In other words: patches
are welcome.

### What is supported

-   ListField, with following value types:
    -   int
    -   float
    -   unicode
    -   datetime
    -   DBRef
    -   Embedded model
    -   (basically these are all types allowed in BSON, except binary
        data, plus DBRef)

-   EmbeddedModelField

### What is NOT supported

-   SetField (I believe it should be extremely easy to implement, but
    since I didn’t need it, I haven’t done it)
-   DictField (why would you need it anyway? It’s much more cleaner to
    use an embedded model)
-   Binary data
-   Lists, etc. inside ListFields (but you can always use an embedded
    model instead)

### Installation

1.  You should get my fork of django-nonrel from bitbucket:

        pip install hg+https://bitbucket.org/v_alexeev/django-nonrel

    It has two small tweaks to the admin app to allow for better
    integration with my widgets and also adds support for list\_filter
    with Mongo.

2.  Then, as usual, you can install my app using pip from either github
    or bitbucket:

        pip install git+https://github.com/V-Alexeev/django_mongodb_extras.git

    or

        pip install hg+https://bitbucket.org/v_alexeev/django_mongodb_extras

3.  Add “django\_mongodb\_extras” to INSTALLED\_APPS in your settings.py
4.  Add something like this to your root urls.py:

        url(r'^admin/nonrel/', include('django_mongodb_extras.urls')),

5.  Then in your models.py import ListField and EmbeddedField from
    django\_mongodb\_extras.fields  (instead of djangotoolbox) and they
    will appear in admin app.
6.  The app uses some static files, so you will have to do “python
    manage.py collectstatic” to use them in non-debug mode.

### How to use Django admin with embedded models

Just put these two lines in your admin.py:

    from django_mongodb_extras.modeladmin import EmbeddedAdmin
    admin.site.register(MyEmbeddedModel, EmbeddedAdmin)

You won’t be able to see a list view of the embedded model, but you will
be able to edit it using a link from its parent model.

### Other “batteries included”

My widgets allow to heavily use DBRefs so I included a couple of
DBRef-specific things for use in your views and templates:

1.   A function to convert a DBRef to model instance:

        from django_mongodb_extras.utils import dbref_to_model_instance

        my_model_instance = dbref_to_model_instance(my_DBRef)

2.  A template tag to convert DBRefs to model instances right inside
    templates:

        {% load nonrel_tags %}

        {% dbref_to_model_instance my_dbref as my_model_instance %}

        {{ my_model_instance.some_field }}
