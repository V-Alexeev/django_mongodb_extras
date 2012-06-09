from django import template

from django_mongodb_extras.utils import dbref_to_model_instance as deref_dbref

register = template.Library()


class DbrefToModelInstanceNode(template.Node):
    def __init__(self, dbref, variable_name):
        self.dbref = template.Variable(dbref)
        self.variable_name = variable_name
    def render(self, context):
        try:
            actual_dbref = self.dbref.resolve(context)
            context[self.variable_name] = deref_dbref(actual_dbref)
        except:
            pass
        return ''

@register.tag()
def dbref_to_model_instance(parser, token):
    try:
        tag_name, dbref, as_keyword, variable_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires 4 arguments" % token.contents.split()[0])
    if as_keyword != "as":
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    return DbrefToModelInstanceNode(dbref, variable_name)