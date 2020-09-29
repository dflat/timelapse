
poll_for_new_frames(interval=5000);

const IMG_THUMB_CLS = "frame-thumb";
const THUMB_CONTAINER_CLS = "frame-thumb-container";
const FRAME_NUMBER_CLS = "frame-number";
const VIDEO_PLAYER_ID = "preview-player";
const PREVIEW_BUTTON_ID = "make-preview-button";
const LOADING_ANIM_SRC = "static/ui/loading.webm";

/** event listeners **/

function docReady(fn) {
    // see if DOM is already available
    if (document.readyState === "complete" || document.readyState === "interactive") {
        // call on next available tick
        setTimeout(fn, 1);
    } else {
        document.addEventListener("DOMContentLoaded", fn);
    }
}  

docReady(function() {
    document.getElementById(PREVIEW_BUTTON_ID)
            .addEventListener('click', generate_video_preview);
    document.addEventListener('keydown', make_video_preview);
});

function make_video_preview(e) {
    var k = e.code;
    if (k == "KeyP") {
        console.log("generating gif preview...");
        generate_gif_preview(e);
    }
}

function generate_gif_preview(e) {
    var frame_count = document.getElementById("frame-count").value;
    console.log(frame_count);
    change_video_source(VIDEO_PLAYER_ID, LOADING_ANIM_SRC); // show loading animation    
    xhr(callback=update_video_preview, endpoint="/api/make_gif_preview/" + frame_count);
}

function generate_video_preview(e) {
    var frame_count = document.getElementById("frame-count").value;
    var fps = document.getElementById("fps").value;
    console.log(frame_count);
    change_video_source(VIDEO_PLAYER_ID, LOADING_ANIM_SRC); // show loading animation    
    var query_string = "?fps=" + fps;
    xhr(callback=update_video_preview, endpoint="/api/make_video_preview/" + frame_count + query_string);
}

function poll_for_new_frames(interval) {
    window.setInterval(xhr, interval, fetch_new_frames, "/api/listdir/frames");
}

function make_thumb_node(src, frame_no) {
    var container = document.createElement("div");
    var img = document.createElement("img");
    var number_display = document.createElement("div");
    var p = document.createElement("p");

    container.classList.add(THUMB_CONTAINER_CLS);
    img.src = src;
    img.alt = frame_no;
    img.classList.add(IMG_THUMB_CLS);
    container.append(img)

    number_display.classList.add(FRAME_NUMBER_CLS);
    p.textContent = frame_no;
    number_display.append(p);
    container.append(number_display)

    return container
}

/** xhr callbacks **/
function fetch_new_frames(xhr_response) {
    var frames = document.getElementById("frames-container");
    var new_frames = JSON.parse(xhr_response.responseText);
    new_frames.forEach(function(f) { frames.prepend(make_thumb_node(f.url, f.number));});
}

function update_video_preview(xhr_response) {
    change_video_source(VIDEO_PLAYER_ID, xhr_response.responseText);
}

function change_video_source(player_id, new_source) {
    var video_player = document.getElementById(player_id);
    var source = video_player.querySelector("source");
    source.src = new_source
    video_player.load();
}

/** main xhr function **/
function xhr(callback, endpoint) {
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            callback(this);
        }
    };
    xhttp.open("GET", endpoint, true);
    xhttp.send();
}

