"""Prompts for real estate listing extraction using Kilo AI Gateway.

Contains Arabic prompts with JSON Schema and few-shot examples for
the kilo-auto/free model. Supports two approaches:
- Method A: Classify then extract (two calls)
- Method B: Single call for both classification and extraction
"""

from __future__ import annotations

import json

# ---------------------------------------------------------------------------
# JSON Schema for structured listing output
# ---------------------------------------------------------------------------

LISTING_SCHEMA = {
    "type": "object",
    "properties": {
        "listing_type": {
            "type": "string",
            "enum": ["for_sale", "for_rent", "buy_or_rent_request", "real_estate_service", "not_real_estate", "unclear"],
            "description": "Type of listing: for_sale ( عقار للبيع ), for_rent ( عقار للإيجار ), buy_or_rent_request ( طلب شراء أو استئجار ), real_estate_service ( خدمات عقارية أو مقاولات ), not_real_estate ( غير متعلق بالعقارات ), unclear ( غير واضح )",
        },
        "property_type": {
            "type": ["string", "null"],
            "description": "Type of property: house ( بيت/دار ), apartment ( شقة ), land ( أرض/قطعة ), villa ( فيلا ), farm ( مزرعة ), or null if not mentioned",
        },
        "title": {
            "type": ["string", "null"],
            "description": "Professional listing title in Arabic, only using information present in the post",
        },
        "description": {
            "type": ["string", "null"],
            "description": "Brief description of the property from the post",
        },
        "city": {
            "type": ["string", "null"],
            "description": "City name (e.g., أربيل, بغداد)",
        },
        "district": {
            "type": ["string", "null"],
            "description": "District or neighborhood name",
        },
        "complex_name": {
            "type": ["string", "null"],
            "description": "Residential complex name (e.g., مجمع اشتي ١, واو تاورز)",
        },
        "area_sqm": {
            "type": ["integer", "null"],
            "description": "Property area in square meters (building area only, not land or garden unless specified)",
        },
        "bedrooms": {
            "type": ["integer", "null"],
            "description": "Number of bedrooms",
        },
        "bathrooms": {
            "type": ["integer", "null"],
            "description": "Number of bathrooms",
        },
        "floor": {
            "type": ["string", "null"],
            "description": "Floor number or level (e.g., 'الطابق 4', 'طابق الأرضي')",
        },
        "furnished": {
            "type": ["boolean", "null"],
            "description": "Whether the property is furnished (مفروشة) or unfurnished (فارغ)",
        },
        "price": {
            "type": ["number", "null"],
            "description": "Price value as mentioned, without currency conversion",
        },
        "currency": {
            "type": ["string", "null"],
            "description": "Currency as mentioned (e.g., دينار, دولار, IQD, USD), or null",
        },
        "contact_phones": {
            "type": ["array", "null"],
            "items": {"type": "string"},
            "description": "Contact phone numbers (extracted locally, not from model)",
        },
        "published_at": {
            "type": ["string", "null"],
            "description": "Post publication timestamp",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Extraction confidence score (0.0 to 1.0)",
        },
    },
    "required": ["listing_type", "confidence"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# Few-shot examples (synthetic, no personal data)
# ---------------------------------------------------------------------------

FEW_SHOT_EXAMPLES = [
    {
        "input": "بيت للبيع في أربيل مجمع اشتي ستي ١\n125 متر + 25 متر حديقة\n4 غرف نوم\nيوجد طابو\nللاستفسار 07000000000",
        "output": {
            "listing_type": "for_sale",
            "property_type": "house",
            "title": "بيت للبيع في أربيل، مجمع اشتي ستي ١",
            "description": "بيت للبيع بمساحة 125 متر مع حديقة 25 متر، 4 غرف نوم، يوجد طابو",
            "city": "أربيل",
            "district": None,
            "complex_name": "مجمع اشتي ستي ١",
            "area_sqm": 125,
            "bedrooms": 4,
            "bathrooms": None,
            "floor": None,
            "furnished": None,
            "price": None,
            "currency": None,
            "contact_phones": [],
            "published_at": None,
            "confidence": 0.9,
        },
    },
    {
        "input": "شقة مفروشة للإيجار في واو تاورز\nمساحة 170م\nثلاث غرف نوم\nالطابق 5\nللاتصال 07000000001",
        "output": {
            "listing_type": "for_rent",
            "property_type": "apartment",
            "title": "شقة مفروشة للإيجار في واو تاورز",
            "description": "شقة مفروشة للإيجار بمساحة 170 متر، 3 غرف نوم، الطابق الخامس",
            "city": "أربيل",
            "district": None,
            "complex_name": "واو تاورز",
            "area_sqm": 170,
            "bedrooms": 3,
            "bathrooms": None,
            "floor": "الطابق 5",
            "furnished": True,
            "price": None,
            "currency": None,
            "contact_phones": [],
            "published_at": None,
            "confidence": 0.9,
        },
    },
    {
        "input": "ابوعلي کردي مقاول عامە\nنشتغل من أساس لحد هيكل بالتقسيط\nلحد مفتاح نقد\nتفليش وتعميربيوت\nللاتصال 07000000002",
        "output": {
            "listing_type": "real_estate_service",
            "property_type": None,
            "title": "خدمات مقاولات عامة",
            "description": "مقاول عام للأعمال من أساس حتى هيكل بالتقسيط ولحد المفتاح نقداً",
            "city": None,
            "district": None,
            "complex_name": None,
            "area_sqm": None,
            "bedrooms": None,
            "bathrooms": None,
            "floor": None,
            "furnished": None,
            "price": None,
            "currency": None,
            "contact_phones": [],
            "published_at": None,
            "confidence": 0.85,
        },
    },
]

# ---------------------------------------------------------------------------
# Method A: Classify then extract (two separate calls)
# ---------------------------------------------------------------------------

CLASSIFY_PROMPT_AR = """أنت خبير في تحليل الإعلانات العقارية على فيسبوك باللغة العربية والكردية.

مهمتك: تصنيف المنشور إلى فئة واحدة فقط من الفئات التالية:

1. for_sale - عقار للبيع (للبيع، بيت للبيع، دار للبيع، شقة للبيع)
2. for_rent - عقار للإيجار (للإيجار، شقة للأيجار، بيت للإيجار)
3. buy_or_rent_request - طلب شراء أو استئجار عقار (أبحث عن، أريد شراء، أريد إيجار)
4. real_estate_service - خدمات عقارية أو مقاولات (مقاول، حدائق، تفليش، تصميم ديكورات، سياج)
5. not_real_estate - غير متعلق بالعقارات
6. unclear - غير واضح ولا يمكن تحديد الفئة

قواعد مهمة:
- خدمات المقاولات والحدائق والتنظيف NOT تعتبر عقارات معروضة للبيع أو الإيجار
- المنشور يجب أن يعرض عقار محدد للبيع أو الإيجار ليصنف as for_sale أو for_rent
- إذا كان النص يطلب خدمة (مثل مقاول לבנות بيت)، صنفه real_estate_service
- دعم النصوص التي تحتوي على عربية وكردية معاً
- لا تخترع معلومات غير موجودة في النص

المنشور:
{post_text}

أجب بصيغة JSON فقط:
{{"category": "الفئة المختارة", "confidence": 0.0-1.0, "reasoning": "شرح مختصر"}}"""

EXTRACT_PROMPT_AR = """أنت خبير في استخراج بيانات الإعلانات العقارية من منشورات فيسبوك باللغة العربية والكردية.

مهمتك: استخراج الحقول المنظمة من المنشور أدناه حسب المخطط المحدد.

القواعد الأساسية:
1. لا تخترع أسعاراً أو مساحات أو مواقع غير مذكورة في النص
2. إذا لم يُذكر حقل، استخدم null
3. افهم الأرقام العربية (١٢٣) والإنجليزية (123) على حد سواء
4. دعم النصوص التي تحتوي على عربية وكردية معاً
5. فرق بين مساحة الأرض ومساحة البناء ومساحة الحديقة عندما يكون ذلك واضحاً
6. لا تحول العملات دون مصدر موثوق
7. أنشئ عنواناً عقارياً احترافياً دون إضافة معلومات غير موجودة
8. أرقام الهواتف يتم استخراجها محلياً، لا تحاول استخراجها من النص
9. إذا كان المنشور لعقار للبيع أو الإيجار، استخرج جميع التفاصيل المتاحة

تصنيف المنشور: {category}

نص المنشور:
{post_text}

مخطط المخرجات (JSON Schema):
{schema_json}

أمثلة توضيحية:
{few_shot_examples}

أجب بصيغة JSON فقط وفقاً للمخطط المحدد أعلاه:"""

# ---------------------------------------------------------------------------
# Method B: Single call for both classification and extraction
# ---------------------------------------------------------------------------

COMBINED_PROMPT_AR = """أنت خبير في تحليل واستخراج بيانات الإعلانات العقارية من منشورات فيسبوك باللغة العربية والكردية.

مهمتك: تصنيف المنشور واستخراج جميع الحقول المنظمة في استدعاء واحد.

الفئات المتاحة للتصنيف:
1. for_sale - عقار للبيع
2. for_rent - عقار للإيجار
3. buy_or_rent_request - طلب شراء أو استئجار
4. real_estate_service - خدمات عقارية أو مقاولات (مقاول، حدائق، إلخ)
5. not_real_estate - غير متعلق بالعقارات
6. unclear - غير واضح

قواعد مهمة:
- خدمات المقاولات والحدائق والتنظيف NOT تعتبر عقارات معروضة للبيع أو الإيجار
- لا تخترع أسعاراً أو مساحات أو مواقع غير مذكورة
- إذا لم يُذكر حقل، استخدم null
- افهم الأرقام العربية (١٢٣) والإنجليزية (123)
- دعم النصوص التي تحتوي على عربية وكردية معاً
- فرق بين مساحة الأرض والبناء والحديقة
- لا تحول العملات
- أرقام الهواتف يتم استخراجها محلياً، لا تستخرجها من النص
- أنشئ عنواناً احترافياً دون إضافة معلومات غير موجودة

نص المنشور:
{post_text}

مخطط المخرجات (JSON Schema):
{schema_json}

أمثلة توضيحية:
{few_shot_examples}

أجب بصيغة JSON فقط وفقاً للمخطط المحدد أعلاه:"""

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def format_few_shot_examples() -> str:
    """Format few-shot examples for the prompt."""
    lines = []
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        lines.append(f"مثال {i}:")
        lines.append(f"النص: {ex['input']}")
        lines.append(f"المخرج: {json.dumps(ex['output'], ensure_ascii=False)}")
        lines.append("")
    return "\n".join(lines)


def format_schema() -> str:
    """Format JSON schema for the prompt."""
    return json.dumps(LISTING_SCHEMA, ensure_ascii=False, indent=2)


def get_classify_prompt(post_text: str) -> str:
    """Get classification prompt in Arabic."""
    return CLASSIFY_PROMPT_AR.format(post_text=post_text[:2000])


def get_extract_prompt(post_text: str, category: str) -> str:
    """Get extraction prompt in Arabic."""
    return EXTRACT_PROMPT_AR.format(
        post_text=post_text[:3000],
        category=category,
        schema_json=format_schema(),
        few_shot_examples=format_few_shot_examples(),
    )


def get_combined_prompt(post_text: str) -> str:
    """Get combined classification+extraction prompt in Arabic."""
    return COMBINED_PROMPT_AR.format(
        post_text=post_text[:3000],
        schema_json=format_schema(),
        few_shot_examples=format_few_shot_examples(),
    )
