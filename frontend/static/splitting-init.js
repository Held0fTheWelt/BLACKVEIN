// Initialize Splitting library for text effects
(function(){
    function runSplitting() {
        if (typeof Splitting !== "function") return;
        var targets = document.querySelectorAll("#hero-title [data-splitting], #void-title [data-splitting]");
        if (targets.length) Splitting({ target: targets });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", runSplitting);
    } else {
        runSplitting();
    }

    window.addEventListener("load", runSplitting);
})();
