var localFixture = false;
var path = '';
var project_path_valid = false;
var image_list_div = null;

function set_fiture_status() {
    callback = function(data, status) {
        if (!data.success) {
            $("#fixture-error-message").html("<em>" + data.reason + "</em>").show();
         } else {
            $("#fixture-error-message").hide();
         }
    };

    error_callback = function() {
        $("#fixture-error-message").html("<em>Fixture file missing</em>").show();
    }

    if (localFixture) {
        $.get("/api/data/fixture/local/" + path.substring(5, path.length), callback).fail(error_callback);
    } else {
        fixt = $(current_fixture_id).val();
        if (fixt) {
            $.get("/api/data/fixture/get/" + fixt, callback).fail(error_callback);
        } else {
            $("#fixture-error-message").hide();
        }
    }
}

function set_project_directory(input) {

    get_path_suggestions(
        input,
        true,
        "",
        function(data, status) {
            path = $(input).val();
            project_path_valid = data.valid_parent && data.exists;
            $("#manual-regridding-source-folder").prop("disabled", !project_path_valid);
            if (project_path_valid) {
                setImageSuggestions(path);
                InputEnabled(image_list_div.find("#manual-selection"), true);
            } else {
                toggleManualSelection(false);
                InputEnabled(image_list_div.find("#manual-selection"), false);
            }

            if (localFixture) {
                set_fiture_status();
            }
            InputEnabled($("#submit-button"), project_path_valid);
    });
}

function setImageSuggestions(path) {

    //Only do stuff if path changed
    if (image_list_div.find("#hidden-path").val() != path)
    {
        image_list_div.find("#hidden-path").val(path);

        image_list_div.find("#manual-selection").prop("checked", false);

        options = image_list_div.find("#options");
        options.empty();

        $.get("/api/compile/image_list/" + path, function(data, status)
        {
            for (var i=0; i<data.images.length; i++)
            {
                row_class = i % 2 == 0 ? 'list-entry-even' : 'list-entry-odd';
                image_data = data.images[i];
                options.append(
                    "<div class='" + row_class + "'>" + String('00' + image_data.index).slice(-3) + ": " +
                    "<input type='checkbox' id='image-data-" + image_data.index + "' checked='checked' value='" + image_data.file + "'>" +
                    "<label class='image-list-label' for='image-data-" + image_data.index + "'>" + image_data.file + "</label></div>");
            }

        });

    }
    else
    {
        toggleManualSelectionBtn(image_list_div.find("#manual-selection"));
    }
}

function toggleManualSelectionBtn(button) {
    toggleManualSelection($(button).prop("checked"));
}

function toggleManualSelection(is_manual) {
    if (is_manual)
    {
        image_list_div.find("#options").show();
        image_list_div.find("#list-buttons").show();
    }
    else
    {
        image_list_div.find("#options").hide();
        image_list_div.find("#list-buttons").hide();
    }
}

function setOnAllImages(included) {
    image_list_div.find("#options").children().each(function () {
        $(this).find(":input").prop("checked", included);
    });
}


function toggleLocalFixture(caller) {
    localFixture = $(caller).prop("checked");
    set_fiture_status();
    InputEnabled($(current_fixture_id), !localFixture);
}

function Compile(button) {

    InputEnabled($(button), false);

    images = null;
    if (image_list_div.find("#manual-selection").prop("checked")) {
        images = [];
        image_list_div.find("#options").children().each(function() {
            imp = $(this).find(":input");
            if (imp.prop("checked") == true) {
                images.push(imp.val());
            }
        });
    }

    data = {local: localFixture ? 1 : 0, 'fixture': $(current_fixture_id).val(),
               path: path,
               chain: $("#chain-analysis-request").is(':checked') ? 0 : 1,
               images: images
            };

    $.ajax({
        url: "?run=1",
        method: "POST",
        data: data,
        success: function (data) {
            if (data.success) {
                Dialogue("Compile", "Compilation enqueued", "", '/status');
            } else {
                Dialogue("Compile", "Compilation Refused", data.reason ? data.reason : "Unknown reason", false, button);
            }

        },
        error: function(data) {
            Dialogue("Compile", "Error", "An error occurred processing the request.", false, button);
        }});
}