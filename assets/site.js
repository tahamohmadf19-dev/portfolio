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

  // Evidence figures: one step or day selected at a time, with arrow keys between them.
  document.querySelectorAll(".check").forEach(function (figure) {
    var buttons = Array.prototype.slice.call(figure.querySelectorAll(".bar-btn, .day-btn"));
    if (!buttons.length) {
      return;
    }
    var points = figure.querySelectorAll(".pt");

    function select(button) {
      buttons.forEach(function (other) {
        var isOpen = other === button;
        other.setAttribute("aria-expanded", isOpen ? "true" : "false");
        var note = document.getElementById(other.getAttribute("aria-controls"));
        note.classList.toggle("is-open", isOpen);
        var row = other.closest(".bar-row");
        if (row) {
          row.classList.toggle("is-open", isOpen);
        }
      });
      var index = button.getAttribute("data-index");
      points.forEach(function (point) {
        point.classList.toggle("is-active", point.getAttribute("data-index") === index);
      });
    }

    buttons.forEach(function (button, index) {
      button.addEventListener("click", function () {
        select(button);
      });
      button.addEventListener("keydown", function (event) {
        var next = null;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") {
          next = buttons[Math.min(index + 1, buttons.length - 1)];
        } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
          next = buttons[Math.max(index - 1, 0)];
        } else if (event.key === "Home") {
          next = buttons[0];
        } else if (event.key === "End") {
          next = buttons[buttons.length - 1];
        }
        if (next) {
          event.preventDefault();
          next.focus();
          select(next);
        }
      });
    });
    // Pointing at a chart point selects its day too.
    points.forEach(function (point) {
      point.addEventListener("click", function () {
        select(buttons[Number(point.getAttribute("data-index"))]);
      });
    });

    // Start on the most telling step: the honest score, or the latest day.
    select(figure.classList.contains("check-co2") ? buttons[2] || buttons[0] : buttons[buttons.length - 1]);
  });

  // Contact form: sent from the page with fetch. Without the script the browser posts the
  // same form to the provider, which redirects to contact-sent.html.
  var form = document.getElementById("contact-form");
  if (form && window.fetch && window.FormData) {
    form.noValidate = true;
    var status = document.getElementById("cf-status");
    var submit = form.querySelector(".form-submit");
    var label = form.querySelector(".form-submit-label");
    var counter = form.querySelector(".counter");
    var loadedAt = Date.now();
    var sending = false;
    var touched = {};
    var email = (document.querySelector('.contact-mail a') || {}).textContent || "";
    var rules = {
      name: function (v) { return v.trim() ? "" : "Enter your name."; },
      email: function (v) {
        if (!v.trim()) { return "Enter your email address, so I can reply."; }
        return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim()) ? "" : "Enter a valid email address, like name@example.com.";
      },
      organization: function (v) { return v.length <= 120 ? "" : "Keep the organization under 120 characters."; },
      inquiry: function (v) { return v ? "" : "Choose what your message is about."; },
      message: function (v) {
        var n = v.trim().length;
        if (n < 20) { return "Write at least 20 characters, so I can reply usefully."; }
        return n <= 4000 ? "" : "Keep the message under 4,000 characters.";
      }
    };
    var fields = Object.keys(rules).map(function (name) { return form.elements[name]; });

    function check(field) {
      var message = rules[field.name](field.value);
      var error = document.getElementById(field.getAttribute("aria-describedby").split(" ").pop());
      error.textContent = message;
      if (message) {
        field.setAttribute("aria-invalid", "true");
      } else {
        field.removeAttribute("aria-invalid");
      }
      return !message;
    }

    function setStatus(kind, text) {
      status.className = "form-status is-" + kind;
      status.textContent = text;
    }

    function setSending(isSending) {
      sending = isSending;
      submit.disabled = isSending;
      form.setAttribute("aria-busy", isSending ? "true" : "false");
      label.textContent = isSending ? "Sending…" : "Send message";
    }

    function fingerprint(values) {
      return [values.name, values.email, values.inquiry, values.message].map(function (v) {
        return String(v).trim().toLowerCase().replace(/\s+/g, " ");
      }).join("|");
    }

    function remembered(key) {
      try { return window.sessionStorage.getItem("contact-sent") === key; } catch (err) { return false; }
    }

    function remember(key) {
      try { window.sessionStorage.setItem("contact-sent", key); } catch (err) { /* private mode: no memory */ }
    }

    fields.forEach(function (field) {
      field.addEventListener("blur", function () {
        if (field.value || touched[field.name]) {
          touched[field.name] = true;
          check(field);
        }
      });
      field.addEventListener("input", function () {
        if (field.getAttribute("aria-invalid") === "true") {
          check(field);
        }
      });
    });
    if (counter) {
      form.elements.message.addEventListener("input", function () {
        counter.textContent = form.elements.message.value.length.toLocaleString("en-US") + " of " +
          Number(counter.getAttribute("data-max")).toLocaleString("en-US");
      });
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (sending) {
        return;
      }
      var invalid = fields.filter(function (field) { touched[field.name] = true; return !check(field); });
      if (invalid.length) {
        setStatus("error", invalid.length === 1 ? "One field needs attention." : invalid.length + " fields need attention.");
        invalid[0].focus();
        return;
      }
      var values = {};
      fields.forEach(function (field) { values[field.name] = field.value.trim(); });
      var key = fingerprint(values);
      if (remembered(key)) {
        setStatus("success", "This message was already sent. There is no need to send it again.");
        status.focus();
        return;
      }
      // Bots: a ticked honeypot or a form sent faster than a person can type it.
      if (form.elements.botcheck.checked) {
        setStatus("success", "Thank you. Your message was sent.");
        return;
      }
      if (Date.now() - loadedAt < 3000) {
        setStatus("error", "That was very quick. Please check your message, then send it again.");
        return;
      }
      var accessKey = form.elements.access_key.value;
      if (!accessKey) {
        setStatus("error", "The form is not connected yet. Please email me at " + email + ".");
        status.focus();
        return;
      }
      if (navigator.onLine === false) {
        setStatus("error", "You seem to be offline. Your message is still here; send it again when you are connected.");
        status.focus();
        return;
      }
      setSending(true);
      setStatus("sending", "Sending your message…");
      var controller = window.AbortController ? new AbortController() : null;
      var timer = controller ? window.setTimeout(function () { controller.abort(); }, 15000) : 0;
      var payload = {
        access_key: accessKey,
        subject: "Portfolio inquiry: " + values.inquiry + " from " + values.name,
        from_name: "Portfolio contact form",
        replyto: values.email,
        name: values.name,
        email: values.email,
        organization: values.organization || "Not given",
        inquiry: values.inquiry,
        message: values.message,
        botcheck: false
      };
      window.fetch(form.getAttribute("action"), {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
        signal: controller ? controller.signal : undefined
      }).then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (body) {
          return { ok: response.ok && body.success === true, status: response.status };
        });
      }).then(function (result) {
        if (result.ok) {
          remember(key);
          form.reset();
          touched = {};
          if (counter) { counter.textContent = "0 of " + Number(counter.getAttribute("data-max")).toLocaleString("en-US"); }
          setStatus("success", "Thank you, " + values.name + ". Your message was sent, and I will reply to " + values.email + ".");
        } else if (result.status === 429) {
          setStatus("error", "Too many messages were sent just now. Please try again later, or email me at " + email + ".");
        } else {
          setStatus("error", "Your message could not be sent. Please try again, or email me at " + email + ".");
        }
      }).catch(function () {
        setStatus("error", "The form service could not be reached. Your message is still here; try again, or email me at " + email + ".");
      }).then(function () {
        window.clearTimeout(timer);
        setSending(false);
        status.focus();
      });
    });
  }

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

  // The verified figures count up once, from zero to the number already written in the page.
  var counters = document.querySelectorAll("[data-count]");
  if (counters.length) {
    var countUp = function (element) {
      var text = element.getAttribute("data-count");
      var target = Number(text.replace(/,/g, ""));
      var start = null;
      var duration = 900;
      function frame(now) {
        if (start === null) {
          start = now;
        }
        var t = Math.min((now - start) / duration, 1);
        var eased = 1 - Math.pow(1 - t, 3);
        element.textContent = t < 1 ? Math.round(target * eased).toLocaleString("en-US") : text;
        if (t < 1) {
          window.requestAnimationFrame(frame);
        }
      }
      window.requestAnimationFrame(frame);
    };
    var counted = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            countUp(entry.target);
            counted.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.6 }
    );
    counters.forEach(function (element) {
      counted.observe(element);
    });
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
