console.log("TEST JS LOADED");
fetch("/api/debug_log?msg=TEST_JS_LOADED");
window.onload = function () {
    console.log("WINDOW LOADED");
    fetch("/api/debug_log?msg=WINDOW_LOADED");
};
