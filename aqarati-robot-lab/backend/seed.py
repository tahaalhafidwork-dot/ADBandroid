"""Safe, non-listing seed data."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DialectTerm

SEED_TERMS = (
    ("طابو", "سند ملكية العقار", "الملكية والتسجيل"),
    ("مشتمل", "وحدة أو بناء تابع ضمن العقار", "وصف مكونات العقار"),
    ("دونم", "وحدة قياس مساحة الأراضي", "مساحات الأراضي"),
    ("شدة", "واجهة أو عرض العقار على الشارع", "وصف أبعاد العقار"),
    ("ورقة", "مبلغ مالي يُقصد به عادةً مئة دولار بحسب السياق", "السعر والتفاوض"),
    ("دفعة", "مبلغ مقدم من السعر", "شروط الدفع"),
    ("أقساط", "دفعات موزعة على مدد زمنية", "شروط الدفع"),
)


def seed_dialect_terms(session: Session) -> None:
    existing = set(session.scalars(select(DialectTerm.term)).all())
    for term, meaning, context in SEED_TERMS:
        if term not in existing:
            session.add(DialectTerm(term=term, meaning=meaning, context=context))

