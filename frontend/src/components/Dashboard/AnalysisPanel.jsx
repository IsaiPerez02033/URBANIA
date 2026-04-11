// Importamos useState para manejar el estado local del campo de ticket de inversión
import { useState } from 'react'
// Importamos el store global para leer y actualizar el sector, parámetros y estado de carga
import { useStore } from '../../store/useStore'
// Importamos las funciones de la API para el demo instantáneo y el análisis personalizado
import { getDemoResult, analyze } from '../../services/api'
// Importamos las utilidades de etiquetas, íconos y formateo de moneda para la interfaz
import { SECTOR_LABELS, SECTOR_ICONS, formatMXN } from '../../utils/colors'

// Declaramos los tres sectores disponibles para el análisis territorial
const SECTORS = ['telecomunicaciones', 'seguridad', 'inmobiliario']

// Declaramos el componente AnalysisPanel que contiene los controles de configuración del análisis
export default function AnalysisPanel({ onResult }) {
  // Leemos y suscribimos el sector activo del store global
  const sector = useStore(s => s.sector)
  // Obtenemos la acción para cambiar el sector activo
  const setSector = useStore(s => s.setSector)
  // Leemos los parámetros financieros del análisis desde el store
  const params = useStore(s => s.params)
  // Obtenemos la acción para actualizar los parámetros financieros
  const setParams = useStore(s => s.setParams)
  // Leemos el indicador de carga para deshabilitar los botones durante el análisis
  const isLoading = useStore(s => s.isLoading)
  // Obtenemos la acción para activar y desactivar el estado de carga
  const setLoading = useStore(s => s.setLoading)
  // Obtenemos la acción para registrar errores en el store global
  const setError = useStore(s => s.setError)
  // Obtenemos la acción para guardar el resultado del análisis en el store
  const setAnalysisResult = useStore(s => s.setAnalysisResult)

  // Declaramos el estado local del campo de ticket para controlar su formato con separadores de miles
  const [ticketInput, setTicketInput] = useState('2,000,000')

  // Cargamos el resultado de demo desde el backend y lo almacenamos en el store
  const loadDemo = async () => {
    setLoading(true)
    setError(null)
    try {
      // Solicitamos el resultado de demo al backend y notificamos al componente padre
      const data = await getDemoResult()
      setAnalysisResult(data)
      onResult && onResult(data)
    } catch (e) {
      setError('No se pudo cargar el demo. Asegúrate de que el backend esté corriendo.')
    } finally {
      setLoading(false)
    }
  }

  // Ejecutamos el análisis personalizado con el sector y parámetros configurados
  const runAnalysis = async () => {
    setLoading(true)
    setError(null)
    try {
      // Enviamos el sector y los parámetros al backend y guardamos el resultado en el store
      const data = await analyze({ sector, params })
      setAnalysisResult(data)
      onResult && onResult(data)
    } catch (e) {
      // Extraemos el mensaje de error del backend o usamos un mensaje genérico
      setError(e?.response?.data?.detail ?? 'Error al ejecutar análisis.')
    } finally {
      setLoading(false)
    }
  }

  // Manejamos el cambio del campo de ticket limpiando caracteres no numéricos y reformateando
  const handleTicket = (val) => {
    // Eliminamos todo lo que no sea dígito para obtener el valor numérico puro
    const raw = val.replace(/[^0-9]/g, '')
    // Formateamos el número con separadores de miles para la visualización en el input
    setTicketInput(Number(raw).toLocaleString())
    // Actualizamos el parámetro numérico en el store para el análisis
    setParams({ ...params, ticket_inversion_mxn: Number(raw) })
  }

  return (
    <div style={{
      height: '100%', overflowY: 'auto', padding: '16px',
      display: 'flex', flexDirection: 'column', gap: 14,
    }}>
      {/* Encabezado con logo y nombre de la plataforma */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
          {/* Ícono de la ciudad como identificador visual de la plataforma */}
          <div style={{
            width: 32, height: 32, borderRadius: 8, background: '#185FA5',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16,
          }}>🏙️</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#e8eaf0' }}>SUSVI</div>
            <div style={{ fontSize: 10, color: '#8b91a8', letterSpacing: '0.08em' }}>INTELIGENCIA TERRITORIAL</div>
          </div>
        </div>
      </div>

      {/* Separador visual entre el encabezado y el selector de sector */}
      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

      {/* Selector de sector de análisis con botones de toggle */}
      <div>
        <Label>Sector de análisis</Label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
          {/* Renderizamos un botón por cada sector disponible */}
          {SECTORS.map(s => (
            <button
              key={s}
              onClick={() => setSector(s)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 12px', borderRadius: 8, textAlign: 'left',
                // Resaltamos el sector activo con borde y fondo azul translúcido
                border: sector === s ? '1px solid #185FA544' : '1px solid rgba(255,255,255,0.07)',
                background: sector === s ? 'rgba(24,95,165,0.2)' : 'rgba(255,255,255,0.03)',
                color: sector === s ? '#e8eaf0' : '#8b91a8',
                cursor: 'pointer', fontSize: 13, fontWeight: sector === s ? 600 : 400,
                transition: 'all 0.15s',
              }}
            >
              <span>{SECTOR_ICONS[s]}</span>
              {SECTOR_LABELS[s]}
              {/* Indicador de selección activa alineado a la derecha */}
              {sector === s && <span style={{ marginLeft: 'auto', fontSize: 10, color: '#185FA5' }}>●</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Separador visual entre el selector de sector y los parámetros financieros */}
      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

      {/* Campos de parámetros financieros del análisis de inversión */}
      <div>
        <Label>Parámetros de inversión</Label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
          {/* Campo de ticket de inversión con formato de miles y prefijo de moneda */}
          <Field
            label="Ticket por unidad (MXN)"
            value={ticketInput}
            onChange={e => handleTicket(e.target.value)}
            prefix="$"
          />
          {/* Campo de vida útil del activo en años para el cálculo de VPN y payback */}
          <Field
            label="Vida útil del activo (años)"
            type="number"
            value={params.vida_util_anios}
            onChange={e => setParams({ ...params, vida_util_anios: Number(e.target.value) })}
            min={1} max={30}
          />
          {/* Campo de tasa de descuento en porcentaje, convertida internamente a decimal */}
          <Field
            label="Tasa de descuento (%)"
            type="number"
            value={(params.tasa_descuento * 100).toFixed(0)}
            onChange={e => setParams({ ...params, tasa_descuento: Number(e.target.value) / 100 })}
            min={1} max={50}
            suffix="%"
          />
          {/* Campo de número de unidades objetivo para dimensionar el escenario de inversión */}
          <Field
            label="Unidades objetivo"
            type="number"
            value={params.n_unidades_objetivo}
            onChange={e => setParams({ ...params, n_unidades_objetivo: Number(e.target.value) })}
            min={1} max={100}
          />
        </div>
      </div>

      {/* Separador visual entre los parámetros y los botones de acción */}
      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

      {/* Botones de acción para lanzar el demo instantáneo o el análisis personalizado */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* Botón de demo instantáneo en ámbar para acceso rápido sin configuración */}
        <button
          onClick={loadDemo}
          disabled={isLoading}
          style={{
            padding: '10px 16px', borderRadius: 10, border: 'none',
            background: isLoading ? '#2a2d3a' : '#EF9F27',
            color: isLoading ? '#8b91a8' : '#1a1200',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontSize: 13, fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            transition: 'all 0.15s',
          }}
        >
          {/* Mostramos spinner durante la carga o el texto del botón cuando está disponible */}
          {isLoading ? (
            <><Spinner /> Procesando…</>
          ) : (
            <>⚡ Cargar Demo CDMX</>
          )}
        </button>

        {/* Botón de análisis personalizado con los parámetros configurados en el panel */}
        <button
          onClick={runAnalysis}
          disabled={isLoading}
          style={{
            padding: '10px 16px', borderRadius: 10,
            border: '1px solid rgba(24,95,165,0.5)',
            background: isLoading ? 'rgba(255,255,255,0.02)' : 'rgba(24,95,165,0.15)',
            color: isLoading ? '#8b91a8' : '#7ab3f0',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontSize: 13, fontWeight: 600,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            transition: 'all 0.15s',
          }}
        >
          🔍 Ejecutar Análisis
        </button>
      </div>

      {/* Indicador de modo que señala el uso del fallback algorítmico cuando Watsonx no responde */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '6px 10px', borderRadius: 8,
        background: 'rgba(29,158,117,0.1)', border: '1px solid rgba(29,158,117,0.25)',
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#1D9E75', flexShrink: 0 }} />
        <span style={{ fontSize: 11, color: '#1D9E75' }}>Modo Demo — IBM Watsonx fallback</span>
      </div>

      {/* Badge de IBM Watsonx al pie del panel para comunicar la tecnología de IA del producto */}
      <div style={{
        marginTop: 'auto', padding: '8px 10px', borderRadius: 8,
        background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 10, color: '#8b91a8' }}>Powered by</div>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#7ab3f0' }}>IBM Watsonx AI</div>
        <div style={{ fontSize: 10, color: '#8b91a8' }}>Granite 13B · 3 Agentes Especializados</div>
      </div>
    </div>
  )
}

// Declaramos el componente de etiqueta de sección en mayúsculas para los grupos de controles
function Label({ children }) {
  return (
    <div style={{ fontSize: 11, fontWeight: 600, color: '#8b91a8', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
      {children}
    </div>
  )
}

// Declaramos el componente de campo de formulario con soporte para prefijo, sufijo y rangos
function Field({ label, value, onChange, type = 'text', prefix, suffix, min, max }) {
  return (
    <div>
      {/* Etiqueta descriptiva del campo en gris secundario */}
      <div style={{ fontSize: 11, color: '#8b91a8', marginBottom: 4 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        {/* Renderizamos el prefijo solo si fue proporcionado como prop */}
        {prefix && <span style={{ fontSize: 12, color: '#8b91a8' }}>{prefix}</span>}
        <input
          type={type}
          value={value}
          onChange={onChange}
          min={min} max={max}
          style={{
            flex: 1, padding: '6px 10px', borderRadius: 6,
            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
            color: '#e8eaf0', fontSize: 13, outline: 'none',
          }}
        />
        {/* Renderizamos el sufijo solo si fue proporcionado como prop */}
        {suffix && <span style={{ fontSize: 12, color: '#8b91a8' }}>{suffix}</span>}
      </div>
    </div>
  )
}

// Declaramos el componente de spinner animado que se muestra durante las operaciones asíncronas
function Spinner() {
  return (
    <div style={{
      width: 14, height: 14, borderRadius: '50%',
      border: '2px solid rgba(255,255,255,0.2)',
      borderTopColor: '#e8eaf0',
      // Aplicamos la animación de giro definida en el CSS global
      animation: 'spin 0.7s linear infinite',
    }} />
  )
}
