django.jQuery(document).ready(function($){
    $("#watchlist-cb").click(function(event){
        event.preventDefault();
        $.ajax({
            url: '/admin/watchlist_add',
            type: 'get',
            dataType: 'json',
            data: {
                id: this.dataset.id,
                model_name: this.dataset.modelName,  // automatically renamed from data-model-name
            },
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", document.csrftoken);
            },
            success: function (data, textStatus, jqXHR) {
                document.getElementById("watchlist-cb").checked = data.on_watchlist;
            }
        });
    });
});

