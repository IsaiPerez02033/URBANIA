export const COLORS = {
  green: '#1D9E75',
  greenLight: '#EAF3DE',
  amber: '#EF9F27',
  amberLight: '#FAEEDA',
  red: '#E24B4A',
  redLight: '#FCEBEB',
  blue: '#185FA5',
  blueLight: '#E6F1FB',
}

export const scoreColor = (score, inverse = false) => {
  if (inverse) score = 100 - score
  if (score >= 65) return COLORS.green
  if (score >= 40) return COLORS.amber
  return COLORS.red
}

export const classColor = (clasificacion) => {
  const map = {
    'Alta viabilidad': COLORS.green,
    'Viabilidad media': COLORS.amber,
    'Descarte': COLORS.red,
    'verde': COLORS.green,
    'cautela': COLORS.amber,
    'descarte': COLORS.red,
    'alta': COLORS.green,
    'media': COLORS.amber,
    'baja': COLORS.red,
  }
  return map[clasificacion] ?? COLORS.blue
}

export const classBadge = (clasificacion) => {
  const bgMap = {
    'Alta viabilidad': 'rgba(29,158,117,0.15)',
    'Viabilidad media': 'rgba(239,159,39,0.15)',
    'Descarte': 'rgba(226,75,74,0.15)',
    'verde': 'rgba(29,158,117,0.15)',
    'cautela': 'rgba(239,159,39,0.15)',
    'descarte': 'rgba(226,75,74,0.15)',
    'alta': 'rgba(29,158,117,0.15)',
    'media': 'rgba(239,159,39,0.15)',
    'baja': 'rgba(226,75,74,0.15)',
  }
  return {
    color: classColor(clasificacion),
    background: bgMap[clasificacion] ?? 'rgba(24,95,165,0.15)',
  }
}

export const formatMXN = (n) => {
  if (!n && n !== 0) return '—'
  const abs = Math.abs(n)
  if (abs >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n.toFixed(0)}`
}

export const formatPct = (n) =>
  n != null ? `${Number(n).toFixed(1)}%` : '—'

export const formatScore = (n) =>
  n != null ? `${Number(n).toFixed(0)}` : '—'

export const SECTOR_LABELS = {
  telecomunicaciones: 'Telecomunicaciones',
  seguridad: 'Seguridad',
  inmobiliario: 'Inmobiliario',
}

export const SECTOR_ICONS = {
  telecomunicaciones: '📡',
  seguridad: '🔐',
  inmobiliario: '🏗️',
}

// Interpolación de color para mapas de calor (score 0-100)
export const scoreToLeafletColor = (score, type = 'demand') => {
  if (type === 'risk') {
    if (score < 30) return COLORS.green
    if (score <= 60) return COLORS.amber
    return COLORS.red
  }
  if (score >= 65) return COLORS.green
  if (score >= 40) return COLORS.amber
  return COLORS.red
}
