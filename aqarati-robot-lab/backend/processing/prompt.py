"""Versioned prompt construction with a locally approved Iraqi glossary."""

from __future__ import annotations

import json
from typing import Any

from .schemas import ExtractionResult

PROMPT_VERSION = "3b.1"


def build_prompt(redacted_text: str, approved_terms: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    schema = ExtractionResult.model_json_schema()
    system = (
        "أنت مستخرج بيانات عقارية عراقية. أعد كائن JSON واحداً فقط يطابق المخطط حرفياً. "
        "لا تخمّن معلومة غير موجودة؛ استخدم null للقيم المجهولة، واذكر الحقول الملتبسة في uncertain_fields. "
        "صنّف البيع والإيجار والخدمات وغير العقاري والمنشور غير الواضح صراحة. افهم الشقق والبيوت "
        "والأراضي والمحلات والمكاتب والمجمعات، والمتر والدونم، والدينار العراقي والدولار. "
        "احتفظ بعبارة السعر والمساحة الأصلية في price_text وarea_text، واجعل السعر null عند عبارات مثل السعر عالخاص. "
        "استخرج قابلية التفاوض والأقساط والدفعة فقط عند ذكرها. استخدم القاموس المعتمد ولا تُعد أي بيانات اتصال."
    )
    glossary = approved_terms or []
    user = (
        "المخطط الصارم:\n" + json.dumps(schema, ensure_ascii=False, separators=(",", ":")) +
        "\nقاموس عراقي معتمد:\n" + json.dumps(glossary, ensure_ascii=False, separators=(",", ":")) +
        "\nالنص المنقح الوحيد المسموح تحليله:\n" + redacted_text
    )
    snapshot = {"prompt_version": PROMPT_VERSION, "schema": schema, "approved_terms": glossary}
    return [{"role": "system", "content": system}, {"role": "user", "content": user}], snapshot
