django.jQuery(function() {
    var $ = django.jQuery;

    $(".vDynamicMultiWidgetAdd").click(function() {
        var last_name = $(this).prev("div").find("[name]").attr("name");
        var re = /(.+)_(\d+)_\d+$/g;
        var match = re.exec(last_name);
        var last_value_number = parseInt(match[2]);
        var value_name = match[1];
        var new_name = value_name + "_" + (last_value_number + 1).toString() + "_";
        var original_div = $(this).prev("div");
        var cloned = original_div.clone(true);
        cloned.hide().insertBefore(this);
        var with_name = cloned.find("[name]");
        var old_with_name = original_div.find("[name]");
        with_name.attr("id", function(index){
                return "id_"+new_name + index.toString();
            }).attr("name", function(index){
                return new_name + index.toString();
            }).val("");
        with_name.each(function(index) {
            $(this).val(function(){
                return $(old_with_name[index]).val();
            });
            $(this).change();
        });
        cloned.fadeIn();
    });
    $(".vDynamicMultiWidgetDelete").click(function () {
        $(this).parent().fadeOut(function() {
            $(this).find("[name]").each(function() {$(this).val(""); $(this).change();});
        });
    });
});