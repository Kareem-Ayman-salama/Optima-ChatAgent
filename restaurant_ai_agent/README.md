# Arabic Restaurant AI Agent Starter

This folder contains the core prototype for an Arabic restaurant assistant that can respond to customers across chat channels such as WhatsApp, Telegram, Messenger, or Facebook.

The important idea is that the first version does not need model fine-tuning. It needs a clear restaurant knowledge base, response rules, and tool-style functions. A production LLM can be added later for more flexible language understanding.

## Contents

- `data/restaurant_knowledge_base.json`: Synthetic production-like restaurant data, including menu items, branches, opening hours, delivery rules, reservation rules, offers, combos, FAQs, allergens, and guardrails.
- `data/restaurant_knowledge_base.small.json`: Smaller backup version of the knowledge base.
- `data/restaurant_intent_dataset.jsonl`: Intent examples for evaluation or future training experiments.
- `data/restaurant_conversation_scenarios.json`: Full conversation scenarios for testing bookings, orders, and complaints.
- `restaurant_agent.py`: Local Arabic assistant logic with menu search, FAQ handling, and reservation/order data collection.
- `sample_conversations.json`: Ready-made test scenarios.
- `simulate_chat.py`: CLI runner for scripted or interactive chat.
- `tools/generate_large_dataset.py`: Generator for rebuilding the large synthetic data files.

## Quick Test

```powershell
python .\restaurant_ai_agent\simulate_chat.py
```

Interactive chat:

```powershell
python .\restaurant_ai_agent\simulate_chat.py --interactive
```

## Run the Streamlit Demo

From the repository root:

```powershell
python -m streamlit run restaurant_ai_agent/streamlit_app.py
```

## Regenerate Data

```powershell
python -B .\restaurant_ai_agent\tools\generate_large_dataset.py
```

The generator writes:

- `data/restaurant_knowledge_base.json`
- `data/restaurant_intent_dataset.jsonl`
- `data/restaurant_conversation_scenarios.json`
- `sample_conversations.json`

## Real Restaurant Data Needed

For a real deployment, replace the synthetic data with:

- Restaurant name, branches, addresses, opening hours, and contact numbers.
- Menu categories, items, descriptions, prices, availability, and tags.
- Reservation rules and required customer fields.
- Delivery areas, minimum order, and expected delivery times.
- FAQ answers and handoff rules.
- Order policies, refund rules, complaint handling, and human escalation rules.

## Next Development Steps

1. Connect one real channel first, usually Telegram for the fastest prototype.
2. Replace local rule-based responses with an LLM that can call structured tools such as `search_menu` and `create_reservation`.
3. Log real conversations only with client approval, then turn them into test cases.
4. Add human handoff for low-confidence responses, complaints, allergies, and sensitive situations.
5. Store reservations and orders in a database instead of temporary in-memory state.

## Notes

- The included dataset is for behavior testing and demos, not model fine-tuning by default.
- The assistant should not invent prices, confirm bookings without availability, or handle serious complaints without human escalation.
- The included restaurant data is synthetic and should not be presented as a real brand menu.
