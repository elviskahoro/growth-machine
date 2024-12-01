from __future__ import annotations

import reflex as rx

from web.pages.index import page

FRONT_CHAT_SCRIPT_URL: str = "https://chat-assets.frontapp.com/v1/chat.bundle.js"
FRONT_CHAT_SCRIPT: str = (
    "window.FrontChat('init', {chatId: 'acc4659ea96842c32ee8c5a2b5de6bfa', useDefaultLauncher: true});"
)
app = rx.App(
    head_components=[
        rx.script(
            src=FRONT_CHAT_SCRIPT_URL,
            strategy="beforeInteractive",
        ),
        rx.script(
            FRONT_CHAT_SCRIPT,
            strategy="afterInteractive",
        ),
    ],
)
app.add_page(
    component=page,
    route="/",
    title="title",
    description="description",
    image="favicon",
    on_load=None,
    meta=[
        {
            "author": "elvis kahoro",
        },
    ],
)
