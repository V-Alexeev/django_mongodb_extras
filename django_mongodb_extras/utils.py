from django.db import models

def dbref_to_model_instance(dbref):
    def get_model_by_table_name(table_name):
        for model in models.get_models():
            if model._meta.db_table == table_name:
                return model
    model = get_model_by_table_name(dbref.collection)
    return model.objects.get(pk=dbref.id)