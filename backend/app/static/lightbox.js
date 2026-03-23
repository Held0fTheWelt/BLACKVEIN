// Lightbox functionality for image gallery
(function() {
    var lightbox = document.getElementById("hero-lightbox");
    var lightboxImg = lightbox && lightbox.querySelector(".lightbox__image");
    var backdrop = lightbox && lightbox.querySelector(".lightbox__backdrop");
    var closeBtn = lightbox && lightbox.querySelector(".lightbox__close");

    function open(src, alt) {
        if (!lightbox || !lightboxImg) return;
        lightboxImg.src = src;
        lightboxImg.alt = alt || "";
        lightbox.setAttribute("aria-hidden", "false");
        lightbox.classList.add("is-open");
        document.body.style.overflow = "hidden";
    }

    function close() {
        if (!lightbox) return;
        lightbox.setAttribute("aria-hidden", "true");
        lightbox.classList.remove("is-open");
        document.body.style.overflow = "";
    }

    document.querySelectorAll(".js-lightbox-open").forEach(function(img) {
        img.addEventListener("click", function() { open(img.src, img.alt); });
    });

    if (backdrop) backdrop.addEventListener("click", close);
    if (closeBtn) closeBtn.addEventListener("click", close);

    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape" && lightbox && lightbox.classList.contains("is-open")) close();
    });
})();
