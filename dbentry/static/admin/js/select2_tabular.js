/*!
 * Django Autocomplete Light - Select2 function
 */

document.addEventListener('dal-init-function', function () {

    yl.registerFunction( 'select2Tabular', function ($, element) {

        var $element = $(element);

        // Templating helper
        function template(text, is_html) {
            if (is_html) {
                // NOTE: will this apply when using highlighting <b> from ts_headline?
                var $result = $('<span>');
                $result.html(text);
                return $result;
            } else {
                return text;
            }
        }

        function result_template(item) {
            var id = item.id;
            var text = template(item.text,
                $element.attr('data-html') !== undefined || $element.attr('data-result-html') !== undefined
            );

            if (item.create_id) {
                return $('<span></span>').text(text).addClass('dal-create')
            }
            if (id === "" || item.loading || item.selected) {
                // Either this is a placeholder, the "loading..." text or
                // we are handling the return value for selected_template().
                return text;
            }
            if (item.is_optgroup){
                if (!item.optgroup_headers.length){
                    // No headers for this optgroup: do not create an optgroup element.
                    return null;
                }
                id = 'ID';
                var column_items = item.optgroup_headers;
            }
            else {
                var column_items = item[$element.data('extra-data-key')]
            }
            var extras = '';
            var textSpan = 10;  // Set the width of the text column to 10.
            if (column_items !== undefined && column_items.length > 0) {
                // Reserve 6 of the 12 bootstrap grid columns for ID (2) and text (4).
                // TODO: what if only one extra column? then extra is wider than text
                // TODO: more than 3 extra columns would leave each column too little space
                textSpan = 4;
                var colSpan = 6 / column_items.length;
                for (key in column_items){
                    extras += `<div class="col-${colSpan}">` + column_items[key] + '</div>'
                }
                // TODO: need to show full page (10 items) at once
            }
            return $(
                '<div class="row">'+
                '<div class="col-2">' + id + '</div>' +
                `<div class="col-${textSpan}">` + text + '</div>' +
                extras +
                '</div>'
            );
        }

        function selected_template(item) {
            if (item.selected_text !== undefined) {
                return template(item.selected_text,
                    $element.attr('data-html') !== undefined || $element.attr('data-selected-html') !== undefined
                );
            } else {
                return result_template(item);
            }
            return
        }

        var ajax = null;
        if ($element.attr('data-autocomplete-light-url')) {
            ajax = {
                url: $element.attr('data-autocomplete-light-url'),
                dataType: 'json',
                delay: 250,

                data: function (params) {
                    var data = {
                        q: params.term, // search term
                        page: params.page,
                        create: $element.attr('data-autocomplete-light-create') && !$element.attr('data-tags'),
                        forward: yl.getForwards($element),
                        tabular: true,
                    };

                    return data;
                },
                processResults: function (data, page) {
                    if ($element.attr('data-tags')) {
                        $.each(data.results, function (index, value) {
                            value.id = value.text;
                        });
                    }

                    return data;
                },
                cache: true
            };
        }

        $element.select2({
            tokenSeparators: $element.attr('data-tags') ? [','] : null,
            debug: true,
            containerCssClass: ':all:',
            placeholder: $element.attr('data-placeholder') || '',
            language: $element.attr('data-autocomplete-light-language'),
            minimumInputLength: $element.attr('data-minimum-input-length') || 0,
            allowClear: !$element.is('[required]'),
            templateResult: result_template,
            templateSelection: selected_template,
            ajax: ajax,
            tags: Boolean($element.attr('data-tags')),
            // width: '100%',
        });

        $element.on('select2:selecting', function (e) {
            var data = e.params.args.data;

            if (data.create_id !== true)
                return;

            e.preventDefault();

            var select = $element;

            $.ajax({
                url: $element.attr('data-autocomplete-light-url'),
                type: 'POST',
                dataType: 'json',
                data: {
                    text: data.id,
                    forward: yl.getForwards($element)
                },
                beforeSend: function (xhr, settings) {
                    xhr.setRequestHeader("X-CSRFToken", document.csrftoken);
                },
                success: function (data, textStatus, jqXHR) {
                    select.append(
                        $('<option>', {value: data.id, text: data.text, selected: true})
                    );
                    select.trigger('change');
                    select.select2('close');
                }
            });
        });
    });
})

