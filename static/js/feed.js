/* FriendHub feed behavior — Developed by Estiuk Arafat Arnob */
(() => {
    "use strict";
    const FH = window.FriendHub;
    if (!FH) return;
    const currentAvatarHtml = document.querySelector(".profile-trigger .avatar")?.outerHTML
        || '<span class="avatar avatar-sm" aria-hidden="true"><span>Y</span></span>';

    const safeUrl = (value = "") => FH.escapeHtml(value);
    const authorUrl = (username) => `/profile/${encodeURIComponent(username)}/`;
    const postUrl = (id) => `/posts/${encodeURIComponent(id)}/`;

    const commentTemplate = (comment) => `
        <div class="comment" id="comment-${comment.id}" data-comment-id="${comment.id}">
            <a href="${authorUrl(comment.author.username)}">${FH.avatarHtml(comment.author, "avatar-sm")}</a>
            <div class="comment__body">
                <div class="comment__bubble"><a href="${authorUrl(comment.author.username)}">${FH.escapeHtml(comment.author.full_name)}</a><p>${FH.escapeHtml(comment.content)}</p></div>
                <span>${FH.escapeHtml(comment.created_display || "Just now")}</span>
            </div>
            ${comment.can_delete ? `<button class="comment-delete" type="button" data-delete-comment="${comment.id}" aria-label="Delete comment">${FH.icon("trash", "icon icon-sm")}</button>` : ""}
        </div>`;

    const postTemplate = (post) => {
        const body = post.content ? `<div class="post-content" data-post-body>${FH.escapeHtml(post.content).replace(/\n/g, "<br>")}</div>` : "";
        const photo = post.image_url ? `<a class="post-image" href="${safeUrl(post.image_url)}" target="_blank" rel="noopener"><img src="${safeUrl(post.image_url)}" alt="Photo shared by ${FH.escapeHtml(post.author.full_name)}" loading="lazy"></a>` : "";
        const comments = (post.recent_comments || []).map(commentTemplate).join("");
        const ownerMenu = post.can_edit ? `
            <div class="dropdown post-menu" data-dropdown>
                <button class="circle-button circle-button--quiet" type="button" aria-label="Post options" aria-expanded="false" data-dropdown-toggle>${FH.icon("more")}</button>
                <div class="dropdown-menu dropdown-menu--right" data-dropdown-menu hidden>
                    <button class="menu-item menu-item--button" type="button" data-edit-post="${post.id}" data-post-content="${FH.escapeHtml(post.content)}" data-has-image="${Boolean(post.image_url)}"><span class="menu-icon">${FH.icon("edit")}</span>Edit post</button>
                    <button class="menu-item menu-item--button menu-item--danger" type="button" data-delete-post="${post.id}"><span class="menu-icon">${FH.icon("trash")}</span>Delete post</button>
                </div>
            </div>` : "";
        return `<article class="card post-card" id="post-${post.id}" data-post-id="${post.id}">
            <header class="post-card__header">
                <a href="${authorUrl(post.author.username)}" class="post-author-avatar" aria-label="View profile">${FH.avatarHtml(post.author, "avatar-md")}</a>
                <div class="post-meta"><a href="${authorUrl(post.author.username)}" class="post-author">${FH.escapeHtml(post.author.full_name)}</a><div class="post-submeta"><a href="${postUrl(post.id)}">${FH.escapeHtml(post.created_display || "Just now")}</a>${post.is_edited ? "<span>· Edited</span>" : ""}<span>·</span>${FH.icon("users", "icon icon-xs")}</div></div>
                ${ownerMenu}
            </header>
            ${body}${photo}
            <div class="post-stats"><span class="like-summary"><span class="reaction-dot">${FH.icon("thumb", "icon icon-xs")}</span><span data-like-count>${post.like_count}</span></span><button type="button" data-comment-toggle>${post.comment_count} <span data-comment-word>comment${post.comment_count === 1 ? "" : "s"}</span></button></div>
            <div class="post-actions">
                <button class="post-action like-button ${post.is_liked ? "is-active" : ""}" type="button" data-like-post="${post.id}" aria-pressed="${post.is_liked}">${FH.icon("thumb")}<span>${post.is_liked ? "Liked" : "Like"}</span></button>
                <button class="post-action" type="button" data-comment-toggle>${FH.icon("comment")}<span>Comment</span></button>
                <button class="post-action" type="button" data-copy-link="${postUrl(post.id)}">${FH.icon("share")}<span>Copy link</span></button>
            </div>
            <section class="comments-panel" aria-label="Comments"><div class="comment-list" data-comment-list>${comments}</div><form class="comment-form" data-comment-form="${post.id}">${currentAvatarHtml}<div class="comment-input-wrap"><label class="sr-only" for="comment-input-${post.id}">Write a comment</label><input id="comment-input-${post.id}" name="content" maxlength="500" placeholder="Write a comment…" autocomplete="off" required><button type="submit" aria-label="Post comment">${FH.icon("send")}</button></div></form></section>
        </article>`;
    };

    const updatePostCount = (card, count) => {
        const counter = card.querySelector(".post-stats [data-comment-toggle]");
        if (counter) counter.innerHTML = `${Number(count)} <span data-comment-word>comment${Number(count) === 1 ? "" : "s"}</span>`;
    };

    const resetCreateForm = (form) => {
        form.reset();
        const preview = document.getElementById("post-image-preview");
        if (preview) { preview.hidden = true; preview.querySelector("img")?.removeAttribute("src"); }
        const counter = document.getElementById("post-counter");
        if (counter) counter.textContent = "0 / 2000";
    };

    document.getElementById("create-post-form")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const button = form.querySelector("button[type='submit']");
        const formData = new FormData(form);
        FH.setLoading(button, true, "Publishing ");
        try {
            const payload = await FH.api("/api/posts/", { method: "POST", body: formData });
            const list = document.getElementById("feed-list");
            if (list) {
                list.querySelector("[data-empty-feed]")?.remove();
                list.insertAdjacentHTML("afterbegin", postTemplate(payload.data));
                document.getElementById(`post-${payload.data.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
            }
            resetCreateForm(form);
            FH.closeModal("create-post-modal");
            FH.toast(payload.message);
        } catch (error) {
            FH.toast(FH.errorMessage(error), "error");
        } finally {
            FH.setLoading(button, false);
        }
    });

    document.getElementById("edit-post-form")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const postId = form.querySelector("[name='post_id']").value;
        const button = form.querySelector("button[type='submit']");
        FH.setLoading(button, true, "Saving ");
        try {
            const payload = await FH.api(`/api/posts/${encodeURIComponent(postId)}/`, { method: "PATCH", body: new FormData(form) });
            const existing = document.getElementById(`post-${postId}`);
            if (existing) {
                const wrapper = document.createElement("div");
                wrapper.innerHTML = postTemplate(payload.data).trim();
                existing.replaceWith(wrapper.firstElementChild);
            }
            FH.closeModal("edit-post-modal");
            FH.toast(payload.message);
        } catch (error) {
            FH.toast(FH.errorMessage(error), "error");
        } finally {
            FH.setLoading(button, false);
        }
    });

    document.addEventListener("submit", async (event) => {
        const form = event.target.closest("[data-comment-form]");
        if (!form) return;
        event.preventDefault();
        const input = form.querySelector("input[name='content']");
        const button = form.querySelector("button[type='submit']");
        const content = input.value.trim();
        if (!content) return;
        button.disabled = true;
        try {
            const payload = await FH.api(`/api/posts/${encodeURIComponent(form.dataset.commentForm)}/comments/`, { method: "POST", body: { content } });
            const card = form.closest(".post-card");
            card.querySelector("[data-comment-list]").insertAdjacentHTML("beforeend", commentTemplate(payload.data));
            card.querySelector(".comments-panel").classList.add("is-open");
            updatePostCount(card, payload.comment_count);
            input.value = "";
        } catch (error) {
            FH.toast(FH.errorMessage(error), "error");
        } finally {
            button.disabled = false;
            input.focus();
        }
    });

    document.addEventListener("click", async (event) => {
        const commentToggle = event.target.closest("[data-comment-toggle]");
        if (commentToggle) {
            const card = commentToggle.closest(".post-card");
            const panel = card.querySelector(".comments-panel");
            panel.classList.toggle("is-open");
            if (panel.classList.contains("is-open")) panel.querySelector("input")?.focus();
            return;
        }

        const likeButton = event.target.closest("[data-like-post]");
        if (likeButton) {
            const card = likeButton.closest(".post-card");
            const liked = likeButton.getAttribute("aria-pressed") === "true";
            likeButton.disabled = true;
            try {
                const payload = await FH.api(`/api/posts/${encodeURIComponent(likeButton.dataset.likePost)}/like/`, { method: liked ? "DELETE" : "POST" });
                likeButton.classList.toggle("is-active", payload.data.is_liked);
                likeButton.setAttribute("aria-pressed", String(payload.data.is_liked));
                likeButton.querySelector("span").textContent = payload.data.is_liked ? "Liked" : "Like";
                card.querySelector("[data-like-count]").textContent = payload.data.like_count;
            } catch (error) {
                FH.toast(FH.errorMessage(error), "error");
            } finally {
                likeButton.disabled = false;
            }
            return;
        }

        const editButton = event.target.closest("[data-edit-post]");
        if (editButton) {
            const form = document.getElementById("edit-post-form");
            form.querySelector("[name='post_id']").value = editButton.dataset.editPost;
            const textarea = form.querySelector("[name='content']");
            textarea.value = editButton.dataset.postContent || "";
            form.querySelector("[name='remove_image']").checked = false;
            form.querySelector("[name='remove_image']").closest("label").hidden = editButton.dataset.hasImage !== "true";
            textarea.dispatchEvent(new Event("input"));
            FH.openModal("edit-post-modal");
            return;
        }

        const deletePost = event.target.closest("[data-delete-post]");
        if (deletePost) {
            const accepted = await FH.confirm("Delete this post permanently? Its likes and comments will also be removed.");
            if (!accepted) return;
            try {
                const payload = await FH.api(`/api/posts/${encodeURIComponent(deletePost.dataset.deletePost)}/`, { method: "DELETE" });
                document.getElementById(`post-${deletePost.dataset.deletePost}`)?.remove();
                FH.toast(payload.message);
            } catch (error) {
                FH.toast(FH.errorMessage(error), "error");
            }
            return;
        }

        const deleteComment = event.target.closest("[data-delete-comment]");
        if (deleteComment) {
            const accepted = await FH.confirm("Delete this comment?", "Delete comment");
            if (!accepted) return;
            try {
                const payload = await FH.api(`/api/comments/${encodeURIComponent(deleteComment.dataset.deleteComment)}/`, { method: "DELETE" });
                const card = deleteComment.closest(".post-card");
                deleteComment.closest(".comment").remove();
                updatePostCount(card, payload.data.comment_count);
                FH.toast(payload.message);
            } catch (error) {
                FH.toast(FH.errorMessage(error), "error");
            }
            return;
        }

        const copyButton = event.target.closest("[data-copy-link]");
        if (copyButton) {
            const url = new URL(copyButton.dataset.copyLink, window.location.origin).href;
            try {
                await navigator.clipboard.writeText(url);
            } catch {
                const area = document.createElement("textarea");
                area.value = url;
                area.style.position = "fixed";
                area.style.opacity = "0";
                document.body.appendChild(area);
                area.select();
                document.execCommand("copy");
                area.remove();
            }
            FH.toast("Post link copied.");
            return;
        }

        const loadMore = event.target.closest("[data-load-more]");
        if (loadMore) {
            const page = Number(loadMore.dataset.nextPage || 2);
            FH.setLoading(loadMore, true, "Loading ");
            try {
                const payload = await FH.api(`/api/feed/?page=${page}`);
                const list = document.getElementById("feed-list");
                payload.data.forEach((post) => list.insertAdjacentHTML("beforeend", postTemplate(post)));
                if (payload.pagination.has_next) {
                    loadMore.dataset.nextPage = String(page + 1);
                    FH.setLoading(loadMore, false);
                } else {
                    loadMore.remove();
                }
            } catch (error) {
                FH.toast(FH.errorMessage(error), "error");
                FH.setLoading(loadMore, false);
            }
        }
    });
})();
