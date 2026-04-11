// Declaramos la paleta de colores corporativa de SUSVI usada en todo el sistema
export const COLORS = {
  green: '#1D9E75',       // Verde para zonas con score alto o viabilidad alta
  greenLight: '#EAF3DE',  // Verde claro para fondos y tarjetas de score positivo
  amber: '#EF9F27',       // Ambar para zonas de cautela o score medio
  amberLight: '#FAEEDA',  // Ambar claro para fondos de advertencia
  red: '#E24B4A',         // Rojo para zonas de descarte o score bajo
  redLight: '#FCEBEB',    // Rojo claro para fondos de alerta
  blue: '#185FA5',        // Azul corporativo para acciones y elementos de marca
  blueLight: '#E6F1FB',   // Azul claro para fondos de elementos de información
}

// Retornamos el color correspondiente al score usando los umbrales del sistema
// El flag inverse invierte la escala para scores donde mayor número = peor (ej. riesgo)
export const scoreColor = (score, inverse = false) => {
  if (inverse) score = 100 - score  // Invertimos para que el riesgo alto sea rojo
  if (score >= 65) return COLORS.green
  if (score >= 40) return COLORS.amber
  return COLORS.red
}

// Retornamos el color de texto para una clasificación cualitativa del sistema SUSVI
export const classColor = (clasificacion) => {
  // Mapeamos todos los tipos de clasificación usados en el sistema a su color correspondiente
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
  // Retornamos azul como color neutro por defecto si la clasificación no está mapeada
  return map[clasificacion] ?? COLORS.blue
}

// Retornamos el objeto de estilo completo (color + background) para un badge de clasificación
export const classBadge = (clasificacion) => {
  // Declaramos los colores de fondo semitransparentes para cada clasificación
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

// Formateamos un número como moneda mexicana abreviada (millones o miles)
export const formatMXN = (n) => {
  if (!n && n !== 0) return '—'  // Retornamos guion si el valor es nulo o indefinido
  const abs = Math.abs(n)
  if (abs >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`  // Expresamos en millones
  if (abs >= 1_000) return `$${(n / 1_000).toFixed(0)}K`           // Expresamos en miles
  return `$${n.toFixed(0)}`                                         // Retornamos sin abreviar
}

// Formateamos un número como porcentaje con un decimal, retornando guion si es nulo
export const formatPct = (n) =>
  n != null ? `${Number(n).toFixed(1)}%` : '—'

// Formateamos un score como número entero sin decimales, retornando guion si es nulo
export const formatScore = (n) =>
  n != null ? `${Number(n).toFixed(0)}` : '—'

// Declaramos las etiquetas legibles para cada sector de análisis del sistema
export const SECTOR_LABELS = {
  telecomunicaciones: 'Telecomunicaciones',
  seguridad: 'Seguridad',
  inmobiliario: 'Inmobiliario',
}

// Declaramos los íconos representativos de cada sector para la interfaz
export const SECTOR_ICONS = {
  telecomunicaciones: '📡',
  seguridad: '🔐',
  inmobiliario: '🏗️',
}

// Retornamos el color de Leaflet correspondiente a un score según el tipo de mapa de calor
export const scoreToLeafletColor = (score, type = 'demand') => {
  if (type === 'risk') {
    // Para el mapa de riesgo invertimos la lógica: score bajo = verde, score alto = rojo
    if (score < 30) return COLORS.green
    if (score <= 60) return COLORS.amber
    return COLORS.red
  }
  // Para demanda y viabilidad usamos los umbrales estándar del sistema
  if (score >= 65) return COLORS.green
  if (score >= 40) return COLORS.amber
  return COLORS.red
}
