export function resolveBackendPort(environment = process.env) {
  const raw = environment.AQARATI_BACKEND_PORT || '8000'
  if (!/^\d+$/.test(raw)) throw new Error('AQARATI_BACKEND_PORT must be an integer')
  const port = Number(raw)
  if (port < 1 || port > 65535) throw new Error('AQARATI_BACKEND_PORT must be between 1 and 65535')
  return port
}

export function backendTarget(environment = process.env) {
  return `http://127.0.0.1:${resolveBackendPort(environment)}`
}
