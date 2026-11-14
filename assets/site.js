// Adds behavior to a page that is already complete: with no script, every section, note and link stays visible.
document.documentElement.classList.add("js");

document.addEventListener("DOMContentLoaded", function () {
  var motionOK = window.matchMedia("(prefers-reduced-motion: no-preference)").matches;

  // System traces: one stage open at a time.
  document.querySelectorAll(".trace").forEach(function (trace) {
    var buttons = Array.prototype.slice.call(trace.querySelectorAll(".stage-btn"));

    function open(button) {
      buttons.forEach(function (other) {
        var isOpen = other === button;
        other.setAttribute("aria-expanded", isOpen ? "true" : "false");
        other.parentElement.classList.toggle("is-open", isOpen);
      });
    }

    buttons.forEach(function (button, index) {
      button.addEventListener("click", function () {
        open(button);
      });
      button.addEventListener("keydown", function (event) {
        var next = null;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") {
          next = buttons[Math.min(index + 1, buttons.length - 1)];
        } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
          next = buttons[Math.max(index - 1, 0)];
        }
        if (next) {
          event.preventDefault();
          next.focus();
          open(next);
        }
      });
    });

    // Open the first control point, because that is the most telling stage of each system.
    open(trace.querySelector(".stage-gate .stage-btn") || buttons[0]);
  });

  // Mobile menu.
  var menuButton = document.querySelector(".menu-btn");
  var menu = document.getElementById("site-nav");
  function setMenu(isOpen) {
    menuButton.setAttribute("aria-expanded", isOpen ? "true" : "false");
    menu.classList.toggle("is-open", isOpen);
  }
  menuButton.addEventListener("click", function () {
    setMenu(menuButton.getAttribute("aria-expanded") !== "true");
  });
  menu.addEventListener("click", function (event) {
    if (event.target.closest("a")) {
      setMenu(false);
    }
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && menuButton.getAttribute("aria-expanded") === "true") {
      setMenu(false);
      menuButton.focus();
    }
  });
  window.matchMedia("(max-width: 760px)").addEventListener("change", function () {
    setMenu(false);
  });

  if (!("IntersectionObserver" in window)) {
    document.querySelectorAll("[data-reveal]").forEach(function (element) {
      element.classList.add("in");
    });
    return;
  }

  // Active section in the navigation.
  var links = {};
  menu.querySelectorAll('a[href^="#"]').forEach(function (link) {
    links[link.getAttribute("href").slice(1)] = link;
  });
  var lastSection = null;
  function setCurrent(current) {
    Object.keys(links).forEach(function (id) {
      if (id === current) {
        links[id].setAttribute("aria-current", "true");
      } else {
        links[id].removeAttribute("aria-current");
      }
    });
  }
  var spy = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          lastSection = entry.target.id;
          setCurrent(lastSection);
        }
      });
    },
    { rootMargin: "-40% 0px -55% 0px" }
  );
  // Contact is too short to reach the middle of the screen, so reaching the footer marks it instead.
  new IntersectionObserver(function (entries) {
    setCurrent(entries[0].isIntersecting ? "contact" : lastSection);
  }).observe(document.querySelector(".foot"));
  document.querySelectorAll("main section[id], #contact").forEach(function (section) {
    if (links[section.id]) {
      spy.observe(section);
    }
  });
  var hero = document.querySelector(".hero");
  if (hero) {
    new IntersectionObserver(
      function (entries) {
        // Above the first section no link is active, and the ambient light rests while it cannot be seen.
        hero.classList.toggle("is-away", !entries[0].isIntersecting);
        if (entries[0].intersectionRatio > 0.6) {
          lastSection = null;
          setCurrent(null);
        }
      },
      { threshold: [0, 0.6] }
    ).observe(hero);
  }

  if (!motionOK) {
    return;
  }

  // Each element appears once, the first time it scrolls into view.
  var reveal = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          reveal.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.08, rootMargin: "0px 0px -6% 0px" }
  );
  document.querySelectorAll("[data-reveal]").forEach(function (element) {
    reveal.observe(element);
  });

  // The hero path runs once after the entrance, and again when someone points at it.
  var path = document.querySelector(".path");
  if (path) {
    var pulse = path.querySelector(".path-pulse");
    var playPath = function () {
      path.classList.add("is-playing");
    };
    pulse.addEventListener("animationend", function () {
      path.classList.remove("is-playing");
    });
    path.addEventListener("pointerenter", playPath);
    window.setTimeout(playPath, 1100);
  }

  // A soft light follows the pointer across a project card, on devices that can hover.
  if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
    document.querySelectorAll(".project").forEach(function (card) {
      var frame = 0;
      card.addEventListener("pointermove", function (event) {
        if (frame) {
          return;
        }
        frame = window.requestAnimationFrame(function () {
          var box = card.getBoundingClientRect();
          card.style.setProperty("--mx", event.clientX - box.left + "px");
          card.style.setProperty("--my", event.clientY - box.top + "px");
          frame = 0;
        });
      });
    });
  }
});
