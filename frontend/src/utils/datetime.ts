/** Parse API timestamps. Naive ISO values are treated as UTC. */
export function parseUtcDate(value: string): Date {
  const trimmed = value.trim()
  const withMs = trimmed.replace(/(\.\d{3})\d+/, '$1')
  if (/[zZ]$/.test(withMs) || /[+-]\d{2}:?\d{2}$/.test(withMs)) {
    return new Date(withMs)
  }
  return new Date(`${withMs}Z`)
}

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

export function formatDate(value: string): string {
  const date = parseUtcDate(value)
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function formatDateTime(value: string): string {
  const date = parseUtcDate(value)
  return `${formatDate(value)} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function formatRelativeDateTime(value: string): string {
  const date = parseUtcDate(value)
  const now = new Date()
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  const clock = `${pad(date.getHours())}:${pad(date.getMinutes())}`
  if (sameDay) return `今天 ${clock}`
  return `${date.getMonth() + 1}月${date.getDate()}日 ${clock}`
}
