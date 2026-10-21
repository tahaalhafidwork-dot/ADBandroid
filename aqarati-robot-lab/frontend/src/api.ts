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
export const labels: Record<string,string> = { for_sale:'للبيع', for_rent:'للإيجار', real_estate_service:'خدمة عقارية', unclear:'غير واضح', not_real_estate:'ليس عقاراً', ok:'مكتمل', completed:'مكتمل', failed:'فاشل', rejected:'مرفوض', draft:'مسودة', needs_review:'بحاجة لمراجعة', approved:'معتمد', duplicate:'مكرر', not_tested:'غير مختبر', connected:'متصل' }
export const label = (value: string | null | undefined) => value ? (labels[value] || value) : 'غير متوفر'
