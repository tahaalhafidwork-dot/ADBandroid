const API = '/api'

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'تعذر الاتصال بالخادم المحلي' }))
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const fmt = (value: number | null | undefined) => value == null ? 'غير متوفر' : new Intl.NumberFormat('ar-IQ').format(value)
export const dateFmt = (value: string | null | undefined) => value ? new Intl.DateTimeFormat('ar-IQ', {dateStyle:'medium', timeStyle:'short'}).format(new Date(value)) : 'غير متوفر'
export const labels: Record<string,string> = { for_sale:'للبيع', for_rent:'للإيجار', real_estate_service:'خدمة عقارية', unclear:'غير واضح', not_real_estate:'ليس عقاراً', ok:'مكتمل', completed:'مكتمل', succeeded:'ناجح', running:'قيد التنفيذ', failed:'فاشل', rejected:'مرفوض', draft:'مسودة', needs_review:'بحاجة لمراجعة', approved:'معتمد', accepted_for_test:'مقبول للاختبار', unreviewed:'غير مراجع', duplicate:'مكرر', not_tested:'غير مختبر', connected:'متصل', valid:'سليم', invalid:'غير صالح', truncated:'مقطوع', not_checked:'غير مفحوص' }
Object.assign(labels, {
  queued:'منتظر', paused:'متوقف مؤقتاً', pause_requested:'طلب إيقاف', canceled:'ملغى',
  cancel_requested:'طلب إلغاء', limit_reached:'بلغ الحد', draft_created:'أُنشئت مسودة',
  corrected:'مصحح', approved_for_sync:'معتمد للمزامنة',
})
export const label = (value: string | null | undefined) => value ? (labels[value] || value) : 'غير متوفر'
