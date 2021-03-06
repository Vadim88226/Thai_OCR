/******************************************************************************
 * HTML5 Multiple File Uploader Demo                                          *
 ******************************************************************************/

// Constants
var MAX_UPLOAD_FILE_SIZE = 1024*1024; // 1 MB
var UPLOAD_URL = "/upload";
var EXPERT_URL = "/expert";
var NEXT_URL   = "/files/";

// List of pending files to handle when the Upload button is finally clicked.
var PENDING_FILES  = [];
$body = $("body");

$(document).on({
    ajaxStart: function() { $body.addClass("loading");    },
    ajaxStop: function() { $body.removeClass("loading"); }
});

$(document).ready(function() {
    // Set up the drag/drop zone.
    initDropbox();

    // Set up the handler for the file input box.
    $("#file-picker").on("change", function(e) {
        var dropbox_text_obj = document.getElementById("dropbox_text");
        dropbox_text_obj.innerHTML = "Or drag and drop files here";
        e.preventDefault();
        handleFiles(this.files);
        doUpload();
    });

    // Handle the submit button.
    $("#upload-button").on("click", function(e) {
        // If the user has JS disabled, none of this code is running but the
        // file multi-upload input box should still work. In this case they'll
        // just POST to the upload endpoint directly. However, with JS we'll do
        // the POST using ajax and then redirect them ourself when done.
        e.preventDefault();
        doUpload();
    })

    // Handle the Expert button
    $("#Export-button").on("click", function(e) {
        e.preventDefault();
        expert_excel();
    })
});

function expert_excel(){
    var xhr = $.ajax({
        url: EXPERT_URL,
        method: "GET",
        contentType: false,
        processData: false,
        cache: false,
        success: function(data) {
            data = JSON.parse(data);
            fileUrl = '../static/uploads/' + data.file;
            var file = new File(["aa"], fileUrl);
            var link = document.createElement("a");
            link.download = 'expert.xlsx';
            link.href = fileUrl;
            link.textContent = data.file;
            link.click();
        },
    });
}

function ajax_call(index) {
    fd = new FormData();
    // Collect the other form data.
    fd.append("file", PENDING_FILES[index]);
    fd.append("__ajax", "true");
    fd.append("index", index)
    var xhr = $.ajax({
        url: UPLOAD_URL,
        method: "POST",
        contentType: false,
        processData: false,
        cache: false,
        data: fd,
        success: function(data) {
            // $progressBar.css({"width": "100%"});
            data = JSON.parse(data);
            processed_image.innerHTML += "Slip " + data.file + " : Done <br>";
            if(index + 1 < PENDING_FILES.length){
                ajax_call(index + 1);
                // How'd it go?
                if (data.status === "error") {
                    // Uh-oh.
                    window.alert(data.msg);
                    $("#upload-form :input").removeAttr("disabled");
                    return;
                }
                else {
                }
            }
        },
        error: function(data) { // 500 Status Header
            processed_image.innerHTML += "Slip " + data.file + " : Failed <br>";
        }
    });
}

function doUpload() {
    // $("#dropbox").children().prop('disabled',true);
    // document.getElementById("dropbox").setAttribute('draggable',false);

    // fd = new FormData();
    var processed_image = document.getElementById('processed_image');
    processed_image.innerHTML = "";

    ajax_call(0);
}


function collectFormData() {
    // Go through all the form fields and collect their names/values.
    var fd = new FormData();

    $("#upload-form :input").each(function() {
        var $this = $(this);
        var name  = $this.attr("name");
        var type  = $this.attr("type") || "";
        var value = $this.val();

        // No name = no care.
        if (name === undefined) {
            return;
        }

        // Skip the file upload box for now.
        if (type === "file") {
            return;
        }

        // Checkboxes? Only add their value if they're checked.
        if (type === "checkbox" || type === "radio") {
            if (!$this.is(":checked")) {
                return;
            }
        }

        fd.append(name, value);
    });

    return fd;
}


function handleFiles(files) {
    // Add them to the pending files list.
    PENDING_FILES = [];
    for (var i = 0, ie = files.length; i < ie; i++) {
        PENDING_FILES.push(files[i]);
    }
}


function initDropbox() {
    var $dropbox = $("#dropbox");
    var $dropbox_text = $("#dropbox_text");

    // On drag enter...
    $dropbox.on("dragenter", function(e) {
        e.stopPropagation();
        e.preventDefault();
        $(this).addClass("active");
    });

    // On drag over...
    $dropbox.on("dragover", function(e) {
        e.stopPropagation();
        e.preventDefault();
    });

    // On drop...
    $dropbox.on("drop", function(e) {
        e.preventDefault();
        $(this).removeClass("active");

        // Get the files.
        var files = e.originalEvent.dataTransfer.files;
        handleFiles(files);

        // Update the display to acknowledge the number of pending files.
        $dropbox_text.text(PENDING_FILES.length + " files ready for upload!");
        $( "#file-picker" ).val("");
        doUpload();
    });

    // If the files are dropped outside of the drop zone, the browser will
    // redirect to show the files in the window. To avoid that we can prevent
    // the 'drop' event on the document.
    function stopDefault(e) {
        e.stopPropagation();
        e.preventDefault();
    }
    $(document).on("dragenter", stopDefault);
    $(document).on("dragover", stopDefault);
    $(document).on("drop", stopDefault);
}