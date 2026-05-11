from __future__ import annotations

import streamlit as st

from restaurant_agent import build_default_agent


st.set_page_config(
    page_title="بيت المذاق | AI Cashier",
    page_icon="",
    layout="centered",
    initial_sidebar_state="collapsed",
)


CUSTOM_CSS = """
<style>
    :root {
        --brand: #185c52;
        --accent: #c27a2c;
        --paper: #fbfaf7;
        --ink: #1f2a2e;
        --muted: #6d777b;
    }

    .stApp {
        direction: rtl;
        background:
            linear-gradient(180deg, rgba(24, 92, 82, 0.10), rgba(251, 250, 247, 0.82) 34%),
            var(--paper);
        color: var(--ink) !important;
    }

    .block-container {
        max-width: 820px;
        padding-top: 1.2rem;
        padding-bottom: 6rem;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    .brand-shell {
        border: 1px solid rgba(31, 42, 46, 0.10);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.78);
        padding: 18px 20px;
        margin-bottom: 18px;
        box-shadow: 0 18px 50px rgba(31, 42, 46, 0.08);
    }

    .brand-row {
        align-items: center;
        display: flex;
        justify-content: space-between;
        gap: 16px;
    }

    .brand-title {
        color: var(--brand);
        font-size: 30px;
        font-weight: 800;
        line-height: 1.1;
        margin: 0;
    }

    .brand-subtitle {
        color: var(--muted);
        font-size: 15px;
        margin-top: 6px;
    }

    .status-pill {
        border: 1px solid rgba(24, 92, 82, 0.18);
        border-radius: 999px;
        color: var(--brand);
        font-size: 13px;
        padding: 7px 11px;
        white-space: nowrap;
    }

    .quick-row {
        display: grid;
        gap: 8px;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin-bottom: 14px;
    }

    div[data-testid="stButton"] > button {
        background: #ffffff !important;
        border-radius: 8px;
        border: 1px solid rgba(24, 92, 82, 0.18);
        color: var(--brand) !important;
        direction: rtl;
        font-weight: 700;
        min-height: 42px;
        width: 100%;
    }

    div[data-testid="stButton"] > button:hover {
        background: #fff8ed !important;
        border-color: rgba(194, 122, 44, 0.65);
        color: var(--accent) !important;
    }

    [data-testid="stChatMessage"] {
        border-radius: 8px;
        border: 1px solid rgba(31, 42, 46, 0.08);
        color: var(--ink) !important;
        margin-bottom: 10px;
        padding: 12px 14px;
    }

    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background: rgba(255, 255, 255, 0.96) !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: #185c52 !important;
        color: #ffffff !important;
    }

    [data-testid="stChatMessage"] p {
        color: var(--ink) !important;
        direction: rtl;
        font-size: 16px;
        line-height: 1.75;
        text-align: right;
    }

    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) p {
        color: #ffffff !important;
    }

    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] div,
    [data-testid="stChatMessage"] span {
        color: inherit !important;
    }

    [data-testid="stChatInput"] textarea {
        direction: rtl;
        text-align: right;
    }

    @media (max-width: 680px) {
        .brand-row {
            align-items: flex-start;
            flex-direction: column;
        }

        .quick-row {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
</style>
"""


QUICK_PROMPTS = [
    "عايز 2 شاورما فراخ وليمون نعناع",
    "تأكيد الطلب",
    "عايز أحجز بكرة الساعة 8",
    "في أكل نباتي؟",
]


def init_state() -> None:
    if "agent" not in st.session_state:
        st.session_state.agent = build_default_agent()
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": st.session_state.agent.welcome(),
            }
        ]


def reset_chat() -> None:
    st.session_state.agent = build_default_agent()
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": st.session_state.agent.welcome(),
        }
    ]


def send_message(message: str) -> None:
    message = message.strip()
    if not message:
        return

    st.session_state.messages.append({"role": "user", "content": message})
    reply = st.session_state.agent.reply(message)
    st.session_state.messages.append({"role": "assistant", "content": reply})


init_state()
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <section class="brand-shell">
        <div class="brand-row">
            <div>
                <h1 class="brand-title">بيت المذاق</h1>
                <div class="brand-subtitle">AI Cashier للمطاعم والطلبات والحجز</div>
            </div>
            <div class="status-pill">متاح الآن</div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

cols = st.columns(len(QUICK_PROMPTS))
for index, prompt in enumerate(QUICK_PROMPTS):
    with cols[index]:
        if st.button(prompt, key=f"quick_{index}"):
            send_message(prompt)
            st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("اكتب رسالتك هنا"):
    send_message(prompt)
    st.rerun()

with st.sidebar:
    st.header("التحكم")
    if st.button("محادثة جديدة"):
        reset_chat()
        st.rerun()
