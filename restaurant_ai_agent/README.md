# Arabic Restaurant AI Agent Starter

ده prototype صغير لفكرة agent مطعم عربي يرد على العملاء في واتساب/تليجرام/مسنجر/فيسبوك.

الفكرة المهمة: مش محتاج dataset تدريب في الأول. محتاج knowledge base واضحة عن المطعم، وقواعد رد، وبعدها ممكن نركب فوقها موديل جاهز زي OpenAI عشان يفهم اللغة بحرية أكتر ويستدعي functions.

## الموجود هنا

- `data/restaurant_knowledge_base.json`: داتا كبيرة production-like لمطعم عربي: 13 قسم، 113 صنف، فروع، مواعيد، توصيل، حجز، إضافات، allergens، عروض، combos، FAQ، وguardrails.
- `data/restaurant_knowledge_base.small.json`: نسخة backup من الداتا الصغيرة الأولى.
- `data/restaurant_intent_dataset.jsonl`: 606 مثال intent لتدريب/تقييم فهم الرسائل.
- `data/restaurant_conversation_scenarios.json`: محادثات كاملة لاختبار الحجز والطلبات والشكاوى.
- `restaurant_agent.py`: agent محلي بسيط يرد بالعربي ويعمل بحث في المنيو ويجمع بيانات الحجز.
- فيه cashier flow بسيط: يضيف أصناف في سلة، يحسب الإجمالي، ويسأل عن دليفري/تيك أواي/أكل في المطعم.
- `sample_conversations.json`: سيناريوهات اختبار.
- `simulate_chat.py`: تشغيل محادثات جاهزة أو تجربة interactive.
- `tools/generate_large_dataset.py`: generator يعيد توليد الداتا الكبيرة بشكل منظم.

## تجربة سريعة

```powershell
python .\restaurant_ai_agent\simulate_chat.py
```

للدردشة يدويًا:

```powershell
python .\restaurant_ai_agent\simulate_chat.py --interactive
```

## إعادة توليد الداتا الكبيرة

```powershell
python -B .\restaurant_ai_agent\tools\generate_large_dataset.py
```

السكريبت يكتب:

- `data/restaurant_knowledge_base.json`
- `data/restaurant_intent_dataset.jsonl`
- `data/restaurant_conversation_scenarios.json`
- `sample_conversations.json`

## شكل الداتا الحقيقي

الداتا اللي محتاجها من أي مطعم غالبًا تكون:

- اسم المطعم، العنوان، المواعيد، رقم التواصل.
- المنيو: الأقسام، الأصناف، السعر، الوصف، هل متاح، tags زي `نباتي` أو `فراخ` أو `غداء`.
- قواعد الحجز: البيانات المطلوبة، الحد الأقصى، طريقة التأكيد.
- قواعد التوصيل: المناطق، المدة، أقل أوردر.
- FAQ: الأسئلة المتكررة وإجاباتها.
- جمل البداية والختام: موجودة تحت `restaurant.conversation`.
- قواعد الطلبات: موجودة تحت `restaurant.order_policy`.
- handoff: إمتى نحول لحد بشري، زي الشكاوى أو الحساسية الشديدة.

## التطوير بعد الـ prototype

1. نوصل agent بقناة واحدة أولًا، ويفضل Telegram للتجربة لأنه أسرع في الإعداد.
2. نبدل الرد المحلي بموديل جاهز، ونخليه يستدعي tools زي `search_menu` و`create_reservation`.
3. نسجل المحادثات الحقيقية بعد موافقة العميل ونطلع منها test cases.
4. نضيف human handoff لما الثقة قليلة أو في مشكلة حساسة.
5. نربطه بقاعدة بيانات للحجوزات والطلبات بدل التخزين المؤقت.

## ملاحظات مهمة

- تدريب موديل من الصفر مش مناسب كبداية. أغلى وأبطأ ومش محتاجينه.
- الـ dataset هنا هدفه تقييم وتجربة السلوك، مش fine-tuning.
- لازم يكون فيه guardrails: ما يخترعش أسعار، ما يؤكدش حجز نهائي إلا بعد توفر فعلي، وما يتعاملش مع شكاوى كبيرة بدون تحويل لبشري.
- الداتا الكبيرة واقعية ومناسبة للديمو، لكنها ليست منيو براند حقيقي ولا أسعار مطعم فعلي. لاستعمال مطعم حقيقي، بدّل الأصناف والأسعار من منيو العميل.
