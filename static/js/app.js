/* FriendHub interactions — Developed by Estiuk Arafat Arnob */
(() => {
    "use strict";

    const sprite = "/static/icons/sprite.svg";
    let lastFocusedElement = null;
    let confirmResolver = null;

    const getCookie = (name) => {
        const match = document.cookie.split("; ").find((row) => row.startsWith(`${name}=`));
        return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : "";
    };

    const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (character) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
    })[character]);

    const icon = (name, className = "icon") => `<svg class="${className}" aria-hidden="true"><use href="${sprite}#${name}"></use></svg>`;

    const api = async (url, options = {}) => {
        const config = { credentials: "same-origin", ...options };
        const method = (config.method || "GET").toUpperCase();
        config.headers = { Accept: "application/json", ...(config.headers || {}) };
        if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
            config.headers["X-CSRFToken"] = getCookie("csrftoken");
        }
        if (config.body && !(config.body instanceof FormData) && typeof config.body !== "string") {
            config.headers["Content-Type"] = "application/json";
            config.body = JSON.stringify(config.body);
        }
        const response = await fetch(url, config);
        let payload;
        try {
            payload = await response.json();
        } catch {
            payload = { success: false, message: "FriendHub received an unexpected response." };
        }
        if (!response.ok || payload.success === false) {
            const error = new Error(payload.message || "Something went wrong. Please try again.");
            error.payload = payload;
            error.status = response.status;
            throw error;
        }
        return payload;
    };

    const toast = (message, type = "success") => {
        const region = document.querySelector("[data-toast-region]");
        if (!region || !message) return;
        const node = document.createElement("div");
        node.className = `toast toast--${type}`;
        node.setAttribute("role", "status");
        node.innerHTML = `<span class="toast__icon">${icon(type === "success" ? "check" : "info", "icon icon-sm")}</span><span class="toast__message"></span><button class="toast__close" type="button" aria-label="Dismiss">${icon("x", "icon icon-sm")}</button>`;
        node.querySelector(".toast__message").textContent = message;
        const remove = () => node.remove();
        node.querySelector("button").addEventListener("click", remove);
        region.appendChild(node);
        window.setTimeout(remove, 4200);
    };

    const errorMessage = (error) => {
        const errors = error?.payload?.errors;
        if (errors && typeof errors === "object") {
            const first = Object.values(errors).flat(Infinity).find(Boolean);
            if (first) return String(first);
        }
        return error?.message || "Something went wrong. Please try again.";
    };

    const openModal = (id) => {
        const modal = document.getElementById(id);
        if (!modal) return;
        lastFocusedElement = document.activeElement;
        modal.hidden = false;
        document.body.classList.add("modal-open");
        window.setTimeout(() => {
            const focusable = modal.querySelector("textarea, input:not([type='hidden']), button, a");
            focusable?.focus();
        }, 40);
    };

    const closeModal = (modalOrId) => {
        const modal = typeof modalOrId === "string" ? document.getElementById(modalOrId) : modalOrId;
        if (!modal) return;
        modal.hidden = true;
        if (!document.querySelector(".modal:not([hidden])")) document.body.classList.remove("modal-open");
        lastFocusedElement?.focus?.();
    };

    const confirmAction = (message, confirmText = "Delete") => new Promise((resolve) => {
        const modal = document.getElementById("confirm-modal");
        if (!modal) return resolve(window.confirm(message));
        modal.querySelector("#confirm-message").textContent = message;
        modal.querySelector("[data-confirm-ok]").textContent = confirmText;
        confirmResolver = resolve;
        openModal("confirm-modal");
    });

    const avatarHtml = (person, size = "avatar-sm") => {
        const image = person.avatar_url
            ? `<img src="${escapeHtml(person.avatar_url)}" alt="" loading="lazy">`
            : `<span>${escapeHtml((person.username || "?").slice(0, 1).toUpperCase())}</span>`;
        return `<span class="avatar ${size}" aria-hidden="true">${image}</span>`;
    };

    const setLoading = (button, loading, fallbackLabel) => {
        if (!button) return;
        if (loading) {
            button.dataset.originalHtml = button.innerHTML;
            button.disabled = true;
            button.classList.add("is-loading");
            button.textContent = fallbackLabel || "Working ";
        } else {
            button.disabled = false;
            button.classList.remove("is-loading");
            button.innerHTML = button.dataset.originalHtml || button.dataset.submitLabel || "Submit";
        }
    };

    const closeDropdowns = (except = null) => {
        document.querySelectorAll("[data-dropdown]").forEach((dropdown) => {
            if (dropdown === except) return;
            const menu = dropdown.querySelector("[data-dropdown-menu]");
            const toggle = dropdown.querySelector("[data-dropdown-toggle]");
            if (menu) menu.hidden = true;
            toggle?.setAttribute("aria-expanded", "false");
        });
    };

    const initializeSearch = () => {
        const root = document.querySelector("[data-search-root]");
        const input = root?.querySelector("[data-live-search]");
        const results = root?.querySelector("[data-search-results]");
        if (!root || !input || !results) return;
        let timer;
        let controller;
        input.addEventListener("input", () => {
            window.clearTimeout(timer);
            controller?.abort();
            const query = input.value.trim();
            if (query.length < 2) {
                results.hidden = true;
                results.innerHTML = "";
                return;
            }
            results.hidden = false;
            results.innerHTML = '<div class="live-search-status">Searching…</div>';
            timer = window.setTimeout(async () => {
                controller = new AbortController();
                try {
                    const payload = await api(`/api/search/?q=${encodeURIComponent(query)}`, { signal: controller.signal });
                    const people = payload.data || [];
                    results.innerHTML = people.length
                        ? people.map((person) => `<a class="live-result" href="/profile/${encodeURIComponent(person.username)}/">${avatarHtml(person)}<span class="live-result__copy"><strong>${escapeHtml(person.full_name)}</strong><span>@${escapeHtml(person.username)}</span></span></a>`).join("") + `<a class="live-search-footer" href="/search/?q=${encodeURIComponent(query)}">See all results</a>`
                        : '<div class="live-search-status">No people found.</div>';
                } catch (error) {
                    if (error.name !== "AbortError") results.innerHTML = '<div class="live-search-status">Search is unavailable right now.</div>';
                }
            }, 280);
        });
        input.addEventListener("focus", () => { if (input.value.trim().length >= 2) results.hidden = false; });
    };

    const updateFollowButtons = (userId, isFollowing) => {
        document.querySelectorAll(`[data-follow-id="${CSS.escape(String(userId))}"]`).forEach((button) => {
            button.dataset.following = String(isFollowing);
            button.textContent = isFollowing ? "Following" : "Follow";
            button.classList.toggle("button--primary", !isFollowing);
            button.classList.toggle("button--secondary", isFollowing);
            button.classList.toggle("button--soft", !isFollowing && !button.closest(".profile-actions"));
            button.setAttribute("aria-pressed", String(isFollowing));
        });
    };

    document.addEventListener("click", async (event) => {
        const modalOpen = event.target.closest("[data-modal-open]");
        if (modalOpen) {
            event.preventDefault();
            openModal(modalOpen.dataset.modalOpen);
            return;
        }
        const modalClose = event.target.closest("[data-modal-close]");
        if (modalClose) {
            closeModal(modalClose.closest(".modal"));
            return;
        }
        const dropdownToggle = event.target.closest("[data-dropdown-toggle]");
        if (dropdownToggle) {
            event.stopPropagation();
            const dropdown = dropdownToggle.closest("[data-dropdown]");
            const menu = dropdown.querySelector("[data-dropdown-menu]");
            const willOpen = menu.hidden;
            closeDropdowns(dropdown);
            menu.hidden = !willOpen;
            dropdownToggle.setAttribute("aria-expanded", String(willOpen));
            return;
        }
        if (!event.target.closest("[data-dropdown]")) closeDropdowns();

        const mobileSearch = event.target.closest("[data-mobile-search]");
        if (mobileSearch) {
            const search = document.querySelector("[data-search-root]");
            search?.classList.toggle("is-mobile-open");
            search?.querySelector("input")?.focus();
            return;
        }

        const followButton = event.target.closest("[data-follow-id]");
        if (followButton) {
            event.preventDefault();
            const userId = followButton.dataset.followId;
            const isFollowing = followButton.dataset.following === "true";
            setLoading(followButton, true, "");
            try {
                const payload = await api(`/api/users/${encodeURIComponent(userId)}/follow/`, { method: isFollowing ? "DELETE" : "POST" });
                updateFollowButtons(userId, payload.data.is_following);
                document.querySelectorAll("[data-profile-follower-count]").forEach((node) => { node.textContent = payload.data.follower_count; });
                toast(payload.message);
            } catch (error) {
                toast(errorMessage(error), "error");
            } finally {
                setLoading(followButton, false);
                updateFollowButtons(userId, document.querySelector(`[data-follow-id="${CSS.escape(String(userId))}"]`)?.dataset.following === "true");
            }
            return;
        }

        const notification = event.target.closest("a[data-notification-id]");
        if (notification && notification.classList.contains("is-unread")) {
            event.preventDefault();
            const href = notification.href;
            try { await api(`/api/notifications/${notification.dataset.notificationId}/read/`, { method: "POST" }); } catch { /* Navigate even if read tracking fails. */ }
            window.location.assign(href);
            return;
        }

        const markAll = event.target.closest("[data-mark-all-read]");
        if (markAll) {
            setLoading(markAll, true, "");
            try {
                await api("/api/notifications/read-all/", { method: "POST" });
                document.querySelectorAll(".is-unread").forEach((item) => item.classList.remove("is-unread"));
                document.querySelectorAll(".unread-dot").forEach((item) => item.remove());
                document.querySelectorAll("[data-unread-badge]").forEach((badge) => { badge.hidden = true; badge.textContent = "0"; });
                markAll.remove();
                toast("All notifications marked as read.");
            } catch (error) {
                toast(errorMessage(error), "error");
                setLoading(markAll, false);
            }
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        const modal = document.querySelector(".modal:not([hidden])");
        if (modal?.id === "confirm-modal" && confirmResolver) {
            const resolver = confirmResolver;
            confirmResolver = null;
            closeModal(modal);
            resolver(false);
        } else if (modal) closeModal(modal);
        closeDropdowns();
    });

    document.querySelector("[data-confirm-cancel]")?.addEventListener("click", () => {
        const resolver = confirmResolver;
        confirmResolver = null;
        closeModal("confirm-modal");
        resolver?.(false);
    });
    document.querySelector("[data-confirm-ok]")?.addEventListener("click", () => {
        const resolver = confirmResolver;
        confirmResolver = null;
        closeModal("confirm-modal");
        resolver?.(true);
    });

    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const input = document.getElementById(button.dataset.passwordToggle);
            if (!input) return;
            const show = input.type === "password";
            input.type = show ? "text" : "password";
            button.textContent = show ? "Hide" : "Show";
            button.setAttribute("aria-label", `${show ? "Hide" : "Show"} password`);
        });
    });

    document.querySelectorAll("[data-char-counter]").forEach((field) => {
        const counter = document.getElementById(field.dataset.charCounter);
        const update = () => {
            if (!counter) return;
            counter.textContent = `${field.value.length} / ${field.maxLength}`;
            counter.classList.toggle("is-near-limit", field.value.length > field.maxLength * .9);
        };
        field.addEventListener("input", update);
        update();
    });

    document.querySelectorAll("[data-image-input]").forEach((input) => {
        input.addEventListener("change", () => {
            const file = input.files?.[0];
            const preview = document.getElementById(input.dataset.imageInput);
            if (!file || !preview) return;
            if (!/^image\/(jpeg|png|webp)$/.test(file.type) || file.size > 5 * 1024 * 1024) {
                input.value = "";
                toast("Choose a JPG, PNG, or WebP image smaller than 5 MB.", "error");
                return;
            }
            const image = document.createElement("img");
            image.alt = "Selected image preview";
            image.src = URL.createObjectURL(file);
            const existing = preview.querySelector("img");
            if (existing) existing.replaceWith(image); else preview.prepend(image);
            preview.querySelector(":scope > span")?.remove();
            preview.hidden = false;
        });
    });

    document.querySelectorAll("[data-clear-image]").forEach((button) => {
        button.addEventListener("click", () => {
            const input = document.getElementById(button.dataset.clearImage);
            const preview = document.getElementById(input?.dataset.imageInput || "");
            if (input) input.value = "";
            if (preview) { preview.hidden = true; preview.querySelector("img")?.removeAttribute("src"); }
        });
    });

    document.querySelectorAll("[data-flash-message]").forEach((node) => {
        const level = node.dataset.level.includes("error") ? "error" : "success";
        toast(node.textContent.trim(), level);
    });

    initializeSearch();

    window.FriendHub = { api, toast, errorMessage, escapeHtml, icon, avatarHtml, openModal, closeModal, confirm: confirmAction, setLoading };
})();
