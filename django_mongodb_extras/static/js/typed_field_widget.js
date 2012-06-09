django.jQuery(function() {
    var $ = django.jQuery;

    $("select.vTypedField").change(function () {
        var event_target = $(this);

        function clean_dbref() {
            event_target.parent().find("a").remove();

            var select = event_target.next("select");
            if (select != null) {
                var old_id = select.attr('id');
                var old_name = select.attr('name');
                var old_val = select.val();
                select.replaceWith("<input type='hidden'/>");
                var hidden = event_target.next('input');
                hidden.attr("id", old_id);
                hidden.attr("name", old_name);
                hidden.val(old_val);
            }
        }

        if (event_target.val() == "DBRef" || event_target.val() == "EmbeddedModel") {
            clean_dbref();
            var ajax_url = "";
            switch (event_target.val()) {
                case "DBRef":
                    ajax_url = __all_models_query_link;
                    break;
                case "EmbeddedModel":
                    ajax_url = __all_embedded_models_query_link;
                    break;
            }
            $.ajax({
                type:"GET",
                data: {},
                dataType: "json",
                url: ajax_url,
                error: function() {
                },
                success: function (data) {
                    var hidden = event_target.next('input');
                    var old_id = hidden.attr('id');
                    var old_name = hidden.attr('name');
                    var old_val = hidden.val();
                    hidden.replaceWith("<select></select>");
                    var select = event_target.next("select");
                    select.attr("id", old_id);
                    select.attr("name", old_name);
                    for (var r in data.result) {
                        select.append("<option value='"+data.result[r]['table_name'] + "'>"+data.result[r]['verbose_name']+"</option>");
                    }
                    select.val(old_val);
                    var input = select.next("input");
                    input.addClass("vForeignKeyRawIdAdminField");
                    input.after(
                        '<a> <img src="/static/admin/img/admin/selector-search.gif" width="16" height="16" alt="'+gettext('Search') + '" /></a>'
                    );
                    var a = input.next("a");
                    a.attr("id", function() {
                        return "lookup_" + input.attr("id");
                    });
                    if (event_target.val() == "DBRef") {
                        a.click(function() { return showRelatedObjectLookupPopup(this);});
                    }
                    select.change(function() {
                        var select = $(this);
                        var a = select.parent().find("a");
                        a.attr('href', function () {
                           var value = select.val();
                           var current_data = {};
                           for (var r in data.result) {
                               if (data.result[r]['table_name'] == value)
                               {
                                   current_data = data.result[r];
                                   break;
                               }
                           }
                           switch (event_target.val()) {
                               case "DBRef":
                                   return current_data['admin_url'] + "/";
                               case "EmbeddedModel":
                                   var re = /(.+)_(\d+)_\d+/;
                                   var match = re.exec(select.attr('name'));
                                   var current_index = match[2];
                                   var field_name = match[1];
                                   if (window.location.href.search(/\/[^\/]+\/[^\/]+\/embedded\/[^\/]+\/[^\/]+\//) > -1) {
                                       re = /.+?\/embedded(.+)$/;
                                       var current_url = re.exec(window.location.href)[1];
                                       return  current_data['admin_url'] + current_url + field_name + "/" + current_index;
                                   } else {
                                       re = /.+\/(.+\/.+\/.+)\/[^\/]*$/;
                                       var current_object_url = re.exec(window.location.href)[1];
                                       return current_data['admin_url'] + "/" + current_object_url + "/" + field_name + "/" + current_index;
                                   }
                           }
                        });
                    });
                    select.change();
                }
            });
        }
        else
        {
            event_target.parent().find("strong").remove();
            clean_dbref();
        }
    });
    $("select.vTypedField").change();
});