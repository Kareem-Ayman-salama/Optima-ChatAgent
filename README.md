# Optima ChatAgent

Optima ChatAgent is an Arabic restaurant assistant prototype for menu search, order support, reservation intake, FAQ handling, and customer-service style responses.

The project is built as a local Python prototype with a rule-based agent, structured restaurant knowledge data, generated intent examples, and a Streamlit interface for demos.

## What It Includes

- Arabic-first restaurant assistant logic.
- Menu and knowledge-base search over structured JSON data.
- Order/cart flow for delivery, takeaway, and dine-in scenarios.
- Reservation data collection flow.
- Scenario files for repeatable conversation tests.
- Streamlit demo app for a simple interactive UI.

## Repository Layout

```text
restaurant_ai_agent/
  restaurant_agent.py                  Core assistant logic.
  streamlit_app.py                     Streamlit demo UI.
  simulate_chat.py                     CLI conversation runner.
  sample_conversations.json            Demo scenarios.
  data/
    restaurant_knowledge_base.json     Main synthetic restaurant knowledge base.
    restaurant_intent_dataset.jsonl    Intent examples for evaluation/training.
    restaurant_conversation_scenarios.json
  tools/
    generate_large_dataset.py          Dataset generator.
```

## Quick Start

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the Streamlit app:

```powershell
python -m streamlit run restaurant_ai_agent/streamlit_app.py
```

Run scripted or interactive chat tests:

```powershell
python restaurant_ai_agent/simulate_chat.py
python restaurant_ai_agent/simulate_chat.py --interactive
```

## Data Note

The included restaurant data is synthetic and designed for demos, testing, and agent-behavior development. Replace menu items, prices, policies, branch details, and FAQs before using the project with a real restaurant.

## Development Notes

The current implementation is useful for validating conversation flow and business rules before connecting a production LLM, channel integration, booking system, or order database.
