from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any


ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
NUMBER_WORDS = {
    "واحد": 1,
    "واحدة": 1,
    "اتنين": 2,
    "اثنين": 2,
    "تلاته": 3,
    "ثلاثه": 3,
    "اربعه": 4,
    "خمسه": 5,
    "سته": 6,
    "سبعه": 7,
    "تمانيه": 8,
    "ثمانيه": 8,
    "تسعه": 9,
    "عشره": 10,
}
WEEKDAYS = {
    "الاثنين": 0,
    "الاتنين": 0,
    "اتنين": 0,
    "الثلاثاء": 1,
    "التلات": 1,
    "التلاتاء": 1,
    "الاربعاء": 2,
    "الاربع": 2,
    "الخميس": 3,
    "الجمعه": 4,
    "الجمعة": 4,
    "السبت": 5,
    "الاحد": 6,
    "الحد": 6,
}


def normalize_text(text: str) -> str:
    text = text.strip().lower().translate(ARABIC_DIGITS)
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ي",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text)
    return text


def extract_first_number(text: str) -> int | None:
    clean = normalize_text(text)
    match = re.search(r"\d+", clean)
    return int(match.group()) if match else None


def extract_first_quantity(text: str) -> int | None:
    clean = normalize_text(text)
    number = extract_first_number(clean)
    if number:
        return number
    for word, value in NUMBER_WORDS.items():
        if word in clean.split():
            return value
    return None


def extract_people(text: str, allow_bare_number: bool = False) -> int | None:
    clean = normalize_text(text)
    has_people_hint = any(word in clean for word in ["فرد", "افراد", "اشخاص", "شخص", "ناس"])
    if re.search(r"(?:\+?20)?01[0125]\d{8}", clean) and not has_people_hint:
        return None
    if not allow_bare_number and not has_people_hint:
        return None
    return extract_first_quantity(clean)


def extract_phone(text: str) -> str | None:
    normalized = text.translate(ARABIC_DIGITS)
    match = re.search(r"(?:\+?20)?01[0125]\d{8}", normalized)
    return match.group() if match else None


def parse_relative_date(text: str, today: date | None = None) -> str | None:
    today = today or date.today()
    raw = text.strip().lower().translate(ARABIC_DIGITS)
    clean = normalize_text(text)
    if "بعد بكره" in clean:
        return (today + timedelta(days=2)).isoformat()
    if any(word in clean for word in ["النهارده", "النهاردا", "اليوم", "دلوقتي"]):
        return today.isoformat()
    if any(word in clean for word in ["بكره", "غدوة", "غدوه"]):
        return (today + timedelta(days=1)).isoformat()

    for weekday, weekday_index in WEEKDAYS.items():
        if normalize_text(weekday) in clean:
            days_ahead = (weekday_index - today.weekday()) % 7
            return (today + timedelta(days=days_ahead)).isoformat()

    iso_match = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", raw)
    if iso_match:
        year, month, day = map(int, iso_match.groups())
        return date(year, month, day).isoformat()

    slash_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](20\d{2}))?\b", raw)
    if slash_match:
        day, month, year = slash_match.groups()
        year_int = int(year) if year else today.year
        return date(year_int, int(month), int(day)).isoformat()

    return None


def parse_time(text: str, allow_bare_number: bool = False) -> str | None:
    clean = normalize_text(text)
    has_time_hint = any(
        word in clean
        for word in [
            "الساعه",
            "ساعة",
            "ساعه",
            "مساء",
            "صباح",
            "ظهر",
            "بالليل",
            "بليل",
            "pm",
            "am",
        ]
    )
    if not allow_bare_number and ":" not in clean and not has_time_hint:
        return None

    match = re.search(r"(?:الساعه|ساعة|ساعه)\s*(\d{1,2})(?::(\d{2}))?", clean)
    if not match:
        match = re.search(r"(\d{1,2})(?::(\d{2}))?", clean)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or "0")
    is_pm = any(word in clean for word in ["مساء", "بليل", "بالليل", "عشا", "عشاء"])
    is_am = any(word in clean for word in ["صباح", "الفجر"])
    is_midnight = any(word in clean for word in ["بليل", "بالليل", "منتصف الليل"])

    if (is_midnight or is_am) and hour == 12:
        hour = 0
    elif is_pm and hour < 12:
        hour += 12
    if not is_pm and not is_am and not is_midnight and 1 <= hour <= 11:
        # Restaurant conversations usually mean afternoon/evening unless the user says morning.
        hour += 12

    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def load_knowledge_base(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


@dataclass
class ConversationState:
    reservation: dict[str, Any] = field(default_factory=dict)
    order: dict[str, Any] = field(default_factory=lambda: {"items": []})
    pending_options: list[dict[str, Any]] = field(default_factory=list)
    awaiting: str | None = None
    last_intent: str | None = None


class RestaurantAgent:
    def __init__(self, knowledge_base: dict[str, Any]) -> None:
        self.kb = knowledge_base
        self.state = ConversationState()
        self.items = self._flatten_items()

    def reset(self) -> None:
        self.state = ConversationState()

    def welcome(self) -> str:
        return self._conversation_text("opening_messages", default=self._greeting())

    def reply(self, message: str) -> str:
        clean = normalize_text(message)
        if not clean:
            return self._conversation_text(
                "empty_message",
                default="أنا معاك. اكتب اسم صنف، أو قول طلب جديد، حجز، دليفري، أو منيو.",
            )

        handoff = self._handoff_if_needed(clean)
        if handoff:
            return handoff

        if self.state.awaiting:
            response = self._continue_waiting_flow(message)
            if response:
                return response

        intent = self._detect_intent(clean)
        self.state.last_intent = intent

        if intent == "greeting":
            return self._greeting(clean)
        if intent == "closing":
            return self._closing()
        if intent == "reservation":
            return self._start_or_update_reservation(message)
        if intent == "order":
            return self._handle_order_message(message)
        if intent == "delivery":
            return self._delivery_info(clean)
        if intent == "hours":
            return self._opening_hours()
        if intent == "location":
            return self._location()
        if intent == "vegetarian":
            return self._items_by_tag("نباتي", intro="أيوه، دي اختيارات نباتي مناسبة:")
        if intent == "price_or_item":
            return self._answer_item_query(clean)
        if intent == "menu":
            return self._menu_summary(clean)

        return self._fallback()

    def _flatten_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for category in self.kb["categories"]:
            for item in category["items"]:
                copied = deepcopy(item)
                copied["category_name"] = category["name"]
                copied["search_text"] = normalize_text(
                    " ".join([item["name"], item["description"], " ".join(item.get("tags", []))])
                )
                items.append(copied)
        return items

    def _handoff_if_needed(self, clean: str) -> str | None:
        triggers = [normalize_text(trigger) for trigger in self.kb.get("handoff", {}).get("triggers", [])]
        if any(trigger in clean for trigger in triggers):
            return self.kb["handoff"]["message"]
        return None

    def _conversation_text(self, key: str, default: str) -> str:
        value = self.kb.get("restaurant", {}).get("conversation", {}).get(key)
        if isinstance(value, list) and value:
            return value[0]
        if isinstance(value, str) and value:
            return value
        return default

    def _detect_intent(self, clean: str) -> str:
        if any(word in clean for word in ["السلام", "اهلا", "هاي", "هلا", "مساء الخير", "صباح الخير"]):
            return "greeting"
        if any(word in clean for word in ["شكرا", "متشكر", "تسلم", "باي", "مع السلامه"]):
            return "closing"
        if self._looks_like_order(clean):
            return "order"
        if any(word in clean for word in ["احجز", "حجز", "ترابيزه", "طربيزه", "ميعاد"]):
            return "reservation"
        if any(word in clean for word in ["توصيل", "دليفري", "بتوصل", "ديليفري", "اقل اوردر", "مينيمم"]):
            return "delivery"
        if any(word in clean for word in ["مفتوح", "مواعيد", "بتقفل", "بتفتح"]):
            return "hours"
        if any(word in clean for word in ["فين", "عنوان", "لوكيشن", "مكانكم"]):
            return "location"
        if any(word in clean for word in ["نباتي", "فيجان", "صيامي"]):
            return "vegetarian"
        if any(
            word in clean
            for word in [
                "منيو",
                "menu",
                "الاصناف",
                "اصناف",
                "كل الاصناف",
                "الاصناف كلها",
                "اكل",
                "غدا",
                "غداء",
                "عشا",
                "عشاء",
                "عندكم ايه",
                "رشحلي",
                "سلطه",
                "سلطة",
                "سلطات",
                "فطار",
                "افطار",
                "اطفال",
                "كيدز",
                "سي فود",
                "بيتزا",
                "باستا",
                "مشويات",
            ]
        ):
            return "menu"
        if any(word in clean for word in ["بكام", "سعر", "كام"]) or self._search_items(clean):
            return "price_or_item"
        return "fallback"

    def _greeting(self, clean: str = "") -> str:
        name = self.kb["restaurant"]["name"]
        opening = self._conversation_text(
            "opening_messages",
            default=f"أهلًا بيك في {name}. تحب تشوف المنيو، تعمل طلب، تحجز ترابيزة، ولا تسأل عن صنف معين؟",
        )
        if "السلام" in clean:
            return f"وعليكم السلام ورحمة الله. {opening}"
        if "مساء" in clean:
            return f"مساء النور. {opening}"
        if "صباح" in clean:
            return f"صباح الفل. {opening}"
        if clean:
            return opening
        return f"أهلًا بيك في {name}. تحب تشوف المنيو، تعمل طلب، تحجز ترابيزة، ولا تسأل عن صنف معين؟"

    def _closing(self) -> str:
        return self._conversation_text(
            "closing_messages",
            default="شكرًا ليك، نورتنا. تحت أمرك في أي وقت.",
        )

    def _menu_summary(self, clean: str) -> str:
        if any(phrase in clean for phrase in ["اعرضلي الاصناف كلها", "الاصناف كلها", "كل الاصناف", "المنيو كله"]):
            return self._full_menu_listing()

        tag_map = {
            "غدا": "غداء",
            "غداء": "غداء",
            "عشا": "عشاء",
            "عشاء": "عشاء",
            "فراخ": "فراخ",
            "لحمه": "لحوم",
            "لحم": "لحوم",
            "سي فود": "سي فود",
            "حلو": "حلو",
            "مشروبات": "بارد",
            "سلطه": "سلطة",
            "سلطة": "سلطة",
            "سلطات": "سلطة",
            "اطفال": "أطفال",
            "كيدز": "أطفال",
            "فطار": "فطار",
            "افطار": "فطار",
            "باستا": "باستا",
            "بيتزا": "بيتزا",
            "مشويات": "مشوي",
            "مشوي": "مشوي",
        }
        for keyword, tag in tag_map.items():
            if normalize_text(keyword) in clean:
                return self._items_by_tag(tag, intro=f"أكيد، دي ترشيحات مناسبة لـ {keyword}:")

        categories = []
        for category in self.kb["categories"]:
            available_count = sum(1 for item in category["items"] if item.get("available", True))
            categories.append(f"{category['name']} ({available_count} اختيارات)")
        return "المنيو عندنا فيه: " + "، ".join(categories) + ". تحب أرشح لك غداء، فراخ، لحوم، نباتي، ولا حلويات؟"

    def _full_menu_listing(self) -> str:
        lines = ["تمام، دي الأصناف كلها حسب الأقسام:"]
        for category in self.kb["categories"]:
            available_items = [item for item in category["items"] if item.get("available", True)]
            if not available_items:
                continue
            compact_items = "، ".join(f"{item['name']} ({item['price_egp']}ج)" for item in available_items)
            lines.append(f"{category['name']}: {compact_items}")
        lines.append("لو تحب أضيف صنف للطلب، اكتب مثلًا: هاخد 2 شاورما فراخ.")
        return "\n".join(lines)

    def _answer_item_query(self, clean: str) -> str:
        matches = self._search_items(clean)
        if not matches:
            return "مش لاقي الصنف ده في المنيو التجريبي. ممكن تكتب اسمه بطريقة تانية أو تقول نوع الأكل اللي محتاجه؟"

        lines = []
        for item in matches[:3]:
            status = "متاح" if item.get("available", True) else "غير متاح حاليًا"
            lines.append(f"{item['name']} بـ {item['price_egp']} جنيه - {status}. {item['description']}")
        return "\n".join(lines)

    def _items_by_tag(self, tag: str, intro: str) -> str:
        clean_tag = normalize_text(tag)
        matches = [
            item
            for item in self.items
            if item.get("available", True)
            and any(clean_tag == normalize_text(item_tag) for item_tag in item.get("tags", []))
        ]
        if not matches:
            return "مش ظاهر عندي اختيارات مناسبة حاليًا. ممكن أوصلك بحد من فريق المطعم يساعدك."
        lines = [intro]
        for item in matches[:4]:
            lines.append(f"- {item['name']}: {item['price_egp']} جنيه. {item['description']}")
        return "\n".join(lines)

    def _search_items(self, clean: str) -> list[dict[str, Any]]:
        query_terms = []
        ignored_terms = {
            "عندكم",
            "عايز",
            "محتاج",
            "هات",
            "ضيف",
            "طلب",
            "اطلب",
            "اوردر",
            "هاخد",
            "اخد",
            "هختار",
            "هاختار",
            "اختار",
            "تمام",
            "طيب",
            "ماشي",
            "ممكن",
            "مع",
            "تاني",
            "واحد",
            "واحدة",
            "اتنين",
            "اثنين",
        }
        for term in clean.split():
            if len(term) <= 2 or term in ignored_terms:
                continue
            query_terms.append(term)
            if term.startswith("ال") and len(term) > 4:
                query_terms.append(term[2:])
            if term.startswith("و") and len(term) > 3:
                query_terms.append(term[1:])
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in self.items:
            score = 0
            for term in query_terms:
                normalized_name = normalize_text(item["name"])
                name_terms = set(normalized_name.split())
                if term in item["search_text"]:
                    score += 2
                if term in normalized_name:
                    score += 3
                if term in name_terms:
                    score += 3
            if score:
                if len(query_terms) == 1 and query_terms[0] not in set(normalize_text(item["name"]).split()):
                    score -= 2
                scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored]

    def _continue_waiting_flow(self, message: str) -> str | None:
        if not self.state.awaiting:
            return None
        if self.state.awaiting == "order.disambiguate":
            return self._continue_order_disambiguation(message)
        if self.state.awaiting.startswith("reservation."):
            return self._continue_reservation(message)
        if self.state.awaiting.startswith("order."):
            return self._continue_order(message)
        return None

    def _looks_like_order(self, clean: str) -> bool:
        order_words = [
            "اطلب",
            "طلب",
            "اوردر",
            "عايز",
            "محتاج",
            "هاخد",
            "اخد",
            "هختار",
            "هاختار",
            "اختار",
            "اختارت",
            "تمام",
            "ماشي",
            "هات",
            "ضيف",
            "زود",
            "احجز",
            "حجز",
            "اكد الطلب",
            "تاكيد الطلب",
        ]
        cart_words = ["السله", "سله", "الطلب", "الاجمالي", "الحساب"]
        if any(phrase in clean for phrase in ["طلب جديد", "اعمل طلب", "اعمل اوردر", "اوردر جديد"]):
            return True
        if any(word in clean for word in ["اكد الطلب", "تاكيد الطلب", "خلص الطلب"]):
            return True
        if any(word in clean for word in cart_words) and self.state.order.get("items"):
            return True
        if self.state.order.get("items") and (self._search_items(clean) or self._generic_category_matches(clean)):
            return True
        if any(word in clean for word in order_words) and self._search_items(clean):
            return True
        if any(word in clean for word in order_words) and any(
            word in clean for word in ["سلطه", "سلطة", "ساندوتش", "مشروب", "صوص"]
        ):
            return True
        return False

    def _handle_order_message(self, message: str) -> str:
        clean = normalize_text(message)

        if any(word in clean for word in ["الغاء", "كانسل", "امسح"]):
            self.state.order = {"items": []}
            self.state.pending_options = []
            self.state.awaiting = None
            return "تمام، لغيت الطلب الحالي. تحب نبدأ طلب جديد؟"

        if self.state.order.get("items") and any(
            word in clean for word in ["اكد الطلب", "تاكيد الطلب", "خلص الطلب", "تمام كده", "كده تمام", "الحساب"]
        ):
            return self._next_order_step()

        generic_matches = self._generic_category_matches(clean)

        matches = self._order_item_matches(clean)
        if not matches:
            if generic_matches:
                return self._ask_which_item(generic_matches)
            if self.state.order.get("items"):
                return self._order_summary(include_next_prompt=True)
            return "قولّي تحب تطلب إيه من المنيو. مثال: عايز 2 شاورما فراخ وليمون نعناع."

        if generic_matches:
            added_lines = []
            direct_specific_matches = [
                item
                for item in matches
                if normalize_text(item["name"]) in clean
                and item["id"] not in {generic_item["id"] for generic_item in generic_matches}
            ]
            for item in direct_specific_matches:
                if item["id"] in {generic_item["id"] for generic_item in generic_matches}:
                    continue
                quantity = self._quantity_for_item(clean, item, multiple_items=True)
                self._add_order_item(item, quantity)
                added_lines.append(f"{quantity} × {item['name']}")
            if added_lines:
                prefix = "تمام، ضفت " + "، ".join(added_lines) + " للطلب.\n"
            else:
                prefix = ""
            return prefix + self._ask_which_item(generic_matches)

        if len(matches) > 1 and not self._has_direct_item_phrase(clean, matches):
            return self._ask_which_item(matches)

        added_lines = []
        for item in matches:
            quantity = self._quantity_for_item(clean, item, multiple_items=len(matches) > 1)
            self._add_order_item(item, quantity)
            added_lines.append(f"{quantity} × {item['name']}")

        added = "، ".join(added_lines)
        self.state.pending_options = []
        return f"تمام، ضفت {added} للطلب.\n{self._order_summary(include_next_prompt=True)}"

    def _generic_category_matches(self, clean: str) -> list[dict[str, Any]]:
        generic_rules = [
            (["سلطه", "سلطة"], lambda item: item["category_name"] == "سلطات"),
            (["ساندوتش"], lambda item: item["category_name"] == "ساندوتشات"),
            (["مشروب"], lambda item: item["category_name"] == "مشروبات"),
        ]
        for keywords, predicate in generic_rules:
            if any(keyword in clean for keyword in keywords):
                category_items = [item for item in self.items if item.get("available", True) and predicate(item)]
                if any(normalize_text(item["name"]) in clean for item in category_items):
                    continue
                return category_items[:5]
        return []

    def _ask_which_item(self, matches: list[dict[str, Any]]) -> str:
        self.state.pending_options = matches[:5]
        self.state.awaiting = "order.disambiguate"
        options = "، ".join(item["name"] for item in self.state.pending_options)
        return f"تقصد أنهي صنف؟ المتاح عندي: {options}."

    def _continue_order_disambiguation(self, message: str) -> str:
        clean = normalize_text(message)
        if any(word in clean for word in ["اكد الطلب", "تاكيد الطلب", "خلص الطلب", "تمام كده", "كده تمام"]):
            self.state.pending_options = []
            self.state.awaiting = None
            return "تمام، مش هضيف اختيار إضافي دلوقتي.\n" + self._next_order_step()

        if self._looks_like_new_order_while_disambiguating(clean):
            self.state.awaiting = None
            self.state.pending_options = []
            return self._handle_order_message(message)

        options = self.state.pending_options
        if not options:
            self.state.awaiting = None
            return self._handle_order_message(message)

        selected = self._select_from_pending_options(clean, options)
        if not selected:
            choices = "، ".join(item["name"] for item in options)
            return f"اختار من دول لو سمحت: {choices}."

        quantity = self._quantity_for_item(clean, selected)
        self._add_order_item(selected, quantity)
        self.state.pending_options = []
        self.state.awaiting = None
        return f"تمام، ضفت {quantity} × {selected['name']} للطلب.\n{self._order_summary(include_next_prompt=True)}"

    def _select_from_pending_options(self, clean: str, options: list[dict[str, Any]]) -> dict[str, Any] | None:
        aliases = {
            "خضرا": "سلطة خضراء",
            "خضراء": "سلطة خضراء",
            "سيزر": "سلطة سيزر فراخ",
            "فتوش": "سلطة فتوش",
            "تبوله": "سلطة تبولة",
            "تبولة": "سلطة تبولة",
            "كفته": "ساندوتش كفتة",
            "كفتة": "ساندوتش كفتة",
            "فاهيتا": "ساندوتش فاهيتا فراخ",
            "فلافل": "ساندوتش فلافل",
        }
        clean_with_alias = clean
        for alias, canonical in aliases.items():
            if alias in clean:
                clean_with_alias += " " + normalize_text(canonical)

        scored: list[tuple[int, dict[str, Any]]] = []
        for item in options:
            score = self._name_overlap_count(clean_with_alias, item)
            normalized_name = normalize_text(item["name"])
            if normalized_name in clean_with_alias:
                score += 4
            if score:
                scored.append((score, item))
        if not scored:
            return None
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[0][1]

    def _looks_like_new_order_while_disambiguating(self, clean: str) -> bool:
        new_order_words = ["عايز", "هاخد", "اخد", "هختار", "هاختار", "اختار", "ضيف", "زود", "هات", "ساندوتش"]
        return any(word in clean for word in new_order_words) and (
            bool(self._search_items(clean)) or bool(self._generic_category_matches(clean))
        )

    def _order_item_matches(self, clean: str) -> list[dict[str, Any]]:
        direct_matches = [item for item in self.items if normalize_text(item["name"]) in clean]
        matches = self._search_items(clean)
        if direct_matches:
            combined: list[dict[str, Any]] = []
            for item in direct_matches:
                if item["id"] in {existing["id"] for existing in combined}:
                    continue
                combined.append(item)
            return combined

        if not matches:
            return []

        first = matches[0]
        overlap = self._name_overlap_count(clean, first)
        if len(matches) == 1 or overlap >= 2:
            return [first]

        unique_single_term_matches = [
            item
            for item in matches
            if self._name_overlap_count(clean, item) >= 1
        ]
        if len(unique_single_term_matches) == 1:
            return unique_single_term_matches
        return matches[:4]

    def _name_overlap_count(self, clean: str, item: dict[str, Any]) -> int:
        query_terms = set(clean.split())
        expanded_terms = set()
        for term in query_terms:
            expanded_terms.add(term)
            if term.startswith("و") and len(term) > 3:
                expanded_terms.add(term[1:])
        return len(set(normalize_text(item["name"]).split()) & expanded_terms)

    def _has_direct_item_phrase(self, clean: str, items: list[dict[str, Any]]) -> bool:
        return any(normalize_text(item["name"]) in clean for item in items)

    def _quantity_for_item(self, clean: str, item: dict[str, Any], multiple_items: bool = False) -> int:
        item_name = normalize_text(item["name"])
        index = clean.find(item_name)
        if index >= 0:
            before = clean[:index].split()[-3:]
            after = clean[index + len(item_name) :].split()[:2]
            nearby = " ".join(before + after)
            quantity = extract_first_quantity(nearby)
            if quantity:
                return quantity
        if multiple_items:
            return 1
        quantity = extract_first_quantity(clean)
        return quantity or 1

    def _add_order_item(self, item: dict[str, Any], quantity: int) -> None:
        order_items = self.state.order.setdefault("items", [])
        for existing in order_items:
            if existing["id"] == item["id"]:
                existing["quantity"] += quantity
                return
        order_items.append(
            {
                "id": item["id"],
                "name": item["name"],
                "price_egp": item["price_egp"],
                "quantity": quantity,
            }
        )

    def _order_total(self) -> int:
        return sum(item["price_egp"] * item["quantity"] for item in self.state.order.get("items", []))

    def _order_summary(self, include_next_prompt: bool = False) -> str:
        order_items = self.state.order.get("items", [])
        if not order_items:
            return "الطلب فاضي حاليًا. تحب تضيف إيه؟"

        lines = ["طلبك الحالي:"]
        for item in order_items:
            line_total = item["price_egp"] * item["quantity"]
            lines.append(f"- {item['quantity']} × {item['name']} = {line_total} جنيه")
        lines.append(f"الإجمالي: {self._order_total()} جنيه")
        if include_next_prompt:
            lines.append(
                self._conversation_text(
                    "order_more_prompt",
                    default="تحب تضيف حاجة تانية؟ لو الطلب كده تمام قول: تأكيد الطلب.",
                )
            )
        return "\n".join(lines)

    def _next_order_step(self) -> str:
        if not self.state.order.get("items"):
            return "لسه مفيش أصناف في الطلب. تحب تطلب إيه؟"

        if "service_type" not in self.state.order:
            self.state.awaiting = "order.service_type"
            return "الطلب هيكون دليفري، تيك أواي، ولا أكل في المطعم؟"

        if self.state.order["service_type"] == "delivery" and "address" not in self.state.order:
            self.state.awaiting = "order.address"
            return "تمام، ابعتلي العنوان بالتفصيل للتوصيل."

        if "name" not in self.state.order:
            self.state.awaiting = "order.name"
            return "الطلب باسم مين؟"

        if "phone" not in self.state.order:
            self.state.awaiting = "order.phone"
            return "ممكن رقم موبايل للتأكيد؟"

        summary = self._finalize_order()
        self.state.order = {"items": []}
        self.state.awaiting = None
        return summary

    def _continue_order(self, message: str) -> str:
        field_name = self.state.awaiting.removeprefix("order.") if self.state.awaiting else ""
        clean = normalize_text(message)

        if field_name == "service_type":
            if any(word in clean for word in ["دليفري", "ديليفري", "توصيل"]):
                self.state.order["service_type"] = "delivery"
            elif any(word in clean for word in ["تيك", "استلام", "اخده", "هاخده", "takeaway"]):
                self.state.order["service_type"] = "takeaway"
            elif any(word in clean for word in ["مطعم", "هنا", "صاله", "ترابيزه"]):
                self.state.order["service_type"] = "dine_in"
            else:
                return "اختار من فضلك: دليفري، تيك أواي، أو أكل في المطعم."
        elif field_name == "address":
            self.state.order["address"] = message.strip()
        elif field_name == "name":
            self.state.order["name"] = message.strip()
        elif field_name == "phone":
            phone = extract_phone(message)
            if not phone:
                return "ممكن رقم موبايل مصري صحيح للتأكيد؟"
            self.state.order["phone"] = phone

        self.state.awaiting = None
        return self._next_order_step()

    def _finalize_order(self) -> str:
        service_labels = {
            "delivery": "دليفري",
            "takeaway": "تيك أواي",
            "dine_in": "أكل في المطعم",
        }
        order = self.state.order
        lines = [
            f"تمام يا {order['name']}، سجلت طلب مبدئي:",
            self._order_summary(include_next_prompt=False),
            f"طريقة الطلب: {service_labels.get(order['service_type'], order['service_type'])}",
        ]
        if order.get("address"):
            lines.append(f"العنوان: {order['address']}")
        lines.append(f"هنأكد على رقم {order['phone']}.")
        lines.append("ملحوظة: التأكيد النهائي والتجهيز بيتم من الكاشير.")
        return "\n".join(lines)

    def _start_or_update_reservation(self, message: str) -> str:
        self._collect_reservation_slots(message)
        return self._next_reservation_step()

    def _continue_reservation(self, message: str) -> str | None:
        field_name = self.state.awaiting.removeprefix("reservation.") if self.state.awaiting else None
        if not field_name:
            return None

        self._collect_reservation_slots(message)
        if field_name in self.state.reservation and field_name in {"date", "people", "time", "phone"}:
            self.state.awaiting = None
            return self._next_reservation_step()

        if field_name == "people":
            people = extract_people(message, allow_bare_number=True)
            if not people:
                return "ممكن عدد الأفراد بالأرقام؟"
            self.state.reservation["people"] = people
        elif field_name == "time":
            time_value = parse_time(message, allow_bare_number=True)
            if not time_value:
                return "ممكن الساعة بصيغة واضحة؟ مثال: 3 أو 8:30 مساءً."
            self.state.reservation["time"] = time_value
        elif field_name == "date":
            date_value = parse_relative_date(message)
            if not date_value:
                return "ممكن اليوم؟ مثال: النهاردة، بكرة، أو 15/5."
            self.state.reservation["date"] = date_value
        elif field_name == "name":
            self.state.reservation["name"] = message.strip()
        elif field_name == "phone":
            phone = extract_phone(message)
            if not phone:
                return "ممكن رقم موبايل مصري صحيح عشان تأكيد الحجز؟"
            self.state.reservation["phone"] = phone

        self.state.awaiting = None
        return self._next_reservation_step()

    def _collect_reservation_slots(self, message: str) -> None:
        reservation = self.state.reservation
        date_value = parse_relative_date(message)
        time_value = parse_time(message)
        people = extract_people(message)
        phone = extract_phone(message)

        if date_value:
            reservation["date"] = date_value
        if time_value:
            reservation["time"] = time_value
        if people and "people" not in reservation:
            reservation["people"] = people
        if phone:
            reservation["phone"] = phone

    def _next_reservation_step(self) -> str:
        reservation = self.state.reservation
        policy = self.kb["restaurant"]["reservation_policy"]

        people = reservation.get("people")
        if people and people > policy["max_people_online"]:
            self.state.awaiting = None
            reservation.clear()
            return "للحجوزات أكبر من 12 شخص، الأفضل تكلمنا على 01000000000 عشان نرتبها صح."

        for required in policy["required_fields"]:
            if required not in reservation:
                self.state.awaiting = f"reservation.{required}"
                prompts = {
                    "name": "تمام. الحجز باسم مين؟",
                    "phone": "ممكن رقم موبايل للتأكيد؟",
                    "date": "تحب الحجز أي يوم؟",
                    "time": "تحب الساعة كام؟",
                    "people": "الحجز كام فرد؟",
                }
                return prompts[required]

        summary = (
            f"تمام يا {reservation['name']}. سجلت طلب حجز مبدئي لـ {reservation['people']} فرد "
            f"يوم {reservation['date']} الساعة {reservation['time']}. "
            f"هنأكد على رقم {reservation['phone']}."
        )
        reservation.clear()
        self.state.awaiting = None
        return summary

    def _delivery_info(self, clean: str) -> str:
        policy = self.kb["restaurant"]["delivery_policy"]
        areas = "، ".join(policy["areas"])
        if "اقل" in clean or "minimum" in clean or "مينيمم" in clean:
            return f"أقل أوردر للتوصيل {policy['minimum_order_egp']} جنيه."
        return f"أيوه، التوصيل متاح في: {areas}. الوقت المتوقع {policy['estimated_minutes']}، وأقل أوردر {policy['minimum_order_egp']} جنيه."

    def _opening_hours(self) -> str:
        hours = self.kb["restaurant"]["opening_hours"]
        return f"مواعيدنا من السبت للأربعاء: {hours['saturday_to_wednesday']}، والخميس والجمعة: {hours['thursday_to_friday']}."

    def _location(self) -> str:
        restaurant = self.kb["restaurant"]
        return f"عنواننا: {restaurant['address']}. اللوكيشن: {restaurant['maps_url']}"

    def _fallback(self) -> str:
        return "ممكن توضّح طلبك أكتر؟ أقدر أساعدك في المنيو، الأسعار، الحجز، المواعيد، أو التوصيل."


def build_default_agent() -> RestaurantAgent:
    data_path = Path(__file__).parent / "data" / "restaurant_knowledge_base.json"
    return RestaurantAgent(load_knowledge_base(data_path))
