/*!
 * Django Autocomplete Light - Select2 function
 */

document.addEventListener('dal-init-function', function () {

    yl.registerFunction( 'select2Tabular', function ($, element) {

        var $element = $(element);

        // Templating helper
        function template(text, is_html) {
            if (is_html) {
                var $result = $('<span>');
                $result.html(text);
                return $result;
            } else {
                return text;
            }
        }

        function result_template(item) {
            let id = item.id;
            let text = template(item.text,
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
            let  column_items;
            if (item.is_optgroup){
                // This is the optgroup for the results. Get the labels/headers
                // for the columns.
                if (!item.optgroup_headers.length){
                    // No headers for this optgroup: do not create an optgroup element.
                    return null;
                }
                id = 'ID';
                column_items = item.optgroup_headers;
            }
            else {
                // Get the data for the extra columns.
                column_items = item[$element.data('extra-data-key')]
            }
            let extras = '';
            if (column_items !== undefined && column_items.length > 0) {
                textSpan = 4;
                // By default, allocate 50% of the width to the extra columns:
                let colWidth = (Math.round(50 / column_items.length * 100) / 100).toString() + "%"
                if (column_items.length == 1){
                    // Just one extra column; allocate a flat 40%.
                    // This leaves more space for the main 'text' column.
                    colWidth = "40%"
                }
                for (key in column_items){
                    extras += `<div class="select2-tabular-result__extra" style="width:${colWidth}">${column_items[key] || '-'}</div>`
                }
            }
            return $(
                '<div class="select2-tabular-results">'+
                '<div class="select2-tabular-result__id">' + id + '</div>' +
                '<div class="select2-tabular-result__text">' + text + '</div>' +
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
                        tabular: true,  // tell the view that grouped data (as per select2 format) is expected
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

