"""Safe, non-listing seed data."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AIProviderConfig, AqaratiIntegrationConfig, DialectTerm

SEED_TERMS = (
    ("طابو", "سند ملكية العقار", "الملكية والتسجيل"),
    ("مشتمل", "وحدة أو بناء تابع ضمن العقار", "وصف مكونات العقار"),
    ("دونم", "وحدة قياس مساحة الأراضي", "مساحات الأراضي"),
    ("شدة", "واجهة أو عرض العقار على الشارع", "وصف أبعاد العقار"),
    ("ورقة", "مبلغ مالي يُقصد به عادةً مئة دولار بحسب السياق", "السعر والتفاوض"),
    ("دفعة", "مبلغ مقدم من السعر", "شروط الدفع"),
    ("أقساط", "دفعات موزعة على مدد زمنية", "شروط الدفع"),
)

PROVIDER_SEEDS = (
    {"provider_key": "kilo", "display_name": "Kilo AI Gateway", "api_base_url": "https://api.kilo.ai/api/gateway", "model_name": "kilo-auto/free", "operation_mode": "cloud", "max_tokens": 1800, "cost_cap": 0},
    {"provider_key": "ollama", "display_name": "Ollama", "api_base_url": "http://127.0.0.1:11434", "operation_mode": "local"},
    {"provider_key": "openvino", "display_name": "OpenVINO", "api_base_url": "http://127.0.0.1:8001", "operation_mode": "local"},
)


def seed_dialect_terms(session: Session) -> None:
    existing = set(session.scalars(select(DialectTerm.term)).all())
    for term, meaning, context in SEED_TERMS:
        if term not in existing:
            session.add(DialectTerm(term=term, meaning=meaning, context=context))


def seed_provider_configs(session: Session) -> None:
    existing = set(session.scalars(select(AIProviderConfig.provider_key)).all())
    for values in PROVIDER_SEEDS:
        if values["provider_key"] not in existing:
            session.add(AIProviderConfig(**values, is_enabled=False, connection_status="not_tested", timeout_seconds=30))


def seed_reference_data(session: Session) -> None:
    seed_dialect_terms(session)
    seed_provider_configs(session)
    if session.get(AqaratiIntegrationConfig, 1) is None:
        session.add(AqaratiIntegrationConfig(
            id=1, service_identity="Aqarati Robot", draft_path="/api/robot/drafts",
            is_enabled=False, connection_status="not_tested",
        ))
