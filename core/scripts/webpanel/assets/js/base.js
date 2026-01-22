$(function () {
    const darkModeToggle = $("#darkModeToggle");
    const darkModeIcon = $("#darkModeIcon");
    const isDarkMode = localStorage.getItem("darkMode") === "enabled";

    setDarkMode(isDarkMode);
    updateIcon(isDarkMode);

    darkModeToggle.on("click", function (e) {
        e.preventDefault();
        const enabled = $("body").hasClass("dark-mode");
        localStorage.setItem("darkMode", enabled ? "disabled" : "enabled");
        setDarkMode(!enabled);
        updateIcon(!enabled);
    });

    function setDarkMode(enabled) {
        $("body").toggleClass("dark-mode", enabled);

        if (enabled) {
            $(".main-header").addClass("navbar-dark").removeClass("navbar-light navbar-white");
            $(".card").addClass("bg-dark");
        } else {
            $(".main-header").addClass("navbar-white navbar-light").removeClass("navbar-dark");
            $(".card").removeClass("bg-dark");
        }
    }

    function updateIcon(enabled) {
        darkModeIcon.removeClass("fa-moon fa-sun")
            .addClass(enabled ? "fa-sun" : "fa-moon");
    }
});