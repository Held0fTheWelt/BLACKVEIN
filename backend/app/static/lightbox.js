// Lightbox functionality for image gallery
(function() {
    function initLightbox() {
        var lightbox = document.getElementById("hero-lightbox");
        var lightboxImg = lightbox && lightbox.querySelector(".lightbox__image");
        var backdrop = lightbox && lightbox.querySelector(".lightbox__backdrop");
        var closeBtn = lightbox && lightbox.querySelector(".lightbox__close");

        if (!lightbox || !lightboxImg) return;

        function open(src, alt) {
            lightboxImg.src = src;
            lightboxImg.alt = alt || "";
            lightbox.setAttribute("aria-hidden", "false");
            lightbox.classList.add("is-open");
            document.body.style.overflow = "hidden";
        }

        function close() {
            lightbox.setAttribute("aria-hidden", "true");
            lightbox.classList.remove("is-open");
            document.body.style.overflow = "";
        }

        document.querySelectorAll(".js-lightbox-open").forEach(function(img) {
            img.addEventListener("click", function(e) {
                e.preventDefault();
                open(img.src, img.alt);
            });
        });

        if (backdrop) backdrop.addEventListener("click", close);
        if (closeBtn) closeBtn.addEventListener("click", close);

        document.addEventListener("keydown", function(e) {
            if (e.key === "Escape" && lightbox.classList.contains("is-open")) close();
        });
    }

    // Wait for DOM to be ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initLightbox);
    } else {
        initLightbox();
    }
})();
