import { useState } from 'react'
import { useStore } from '../../store/useStore'
import { getDemoResult, analyze } from '../../services/api'
import { SECTOR_LABELS, SECTOR_ICONS, formatMXN } from '../../utils/colors'

const SECTORS = ['telecomunicaciones', 'seguridad', 'inmobiliario']

export default function AnalysisPanel({ onResult }) {
  const sector = useStore(s => s.sector)
  const setSector = useStore(s => s.setSector)
  const params = useStore(s => s.params)
  const setParams = useStore(s => s.setParams)
  const isLoading = useStore(s => s.isLoading)
  const setLoading = useStore(s => s.setLoading)
  const setError = useStore(s => s.setError)
  const setAnalysisResult = useStore(s => s.setAnalysisResult)

  const [ticketInput, setTicketInput] = useState('2,000,000')

  const loadDemo = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getDemoResult()
      setAnalysisResult(data)
      onResult && onResult(data)
    } catch (e) {
      setError('No se pudo cargar el demo. Asegúrate de que el backend esté corriendo.')
    } finally {
      setLoading(false)
    }
  }

  const runAnalysis = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await analyze({ sector, params })
      setAnalysisResult(data)
      onResult && onResult(data)
    } catch (e) {
      setError(e?.response?.data?.detail ?? 'Error al ejecutar análisis.')
    } finally {
      setLoading(false)
    }
  }

  const handleTicket = (val) => {
    const raw = val.replace(/[^0-9]/g, '')
    setTicketInput(Number(raw).toLocaleString())
    setParams({ ...params, ticket_inversion_mxn: Number(raw) })
  }

  return (
    <div style={{
      height: '100%', overflowY: 'auto', padding: '16px',
      display: 'flex', flexDirection: 'column', gap: 14,
    }}>
      {/* Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8, background: '#185FA5',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16,
          }}>🏙️</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#e8eaf0' }}>URBANIA</div>
            <div style={{ fontSize: 10, color: '#8b91a8', letterSpacing: '0.08em' }}>INTELIGENCIA TERRITORIAL</div>
          </div>
        </div>
      </div>

      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

      {/* Sector */}
      <div>
        <Label>Sector de análisis</Label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
          {SECTORS.map(s => (
            <button
              key={s}
              onClick={() => setSector(s)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 12px', borderRadius: 8, textAlign: 'left',
                border: sector === s ? '1px solid #185FA544' : '1px solid rgba(255,255,255,0.07)',
                background: sector === s ? 'rgba(24,95,165,0.2)' : 'rgba(255,255,255,0.03)',
                color: sector === s ? '#e8eaf0' : '#8b91a8',
                cursor: 'pointer', fontSize: 13, fontWeight: sector === s ? 600 : 400,
                transition: 'all 0.15s',
              }}
            >
              <span>{SECTOR_ICONS[s]}</span>
              {SECTOR_LABELS[s]}
              {sector === s && <span style={{ marginLeft: 'auto', fontSize: 10, color: '#185FA5' }}>●</span>}
            </button>
          ))}
        </div>
      </div>

      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

      {/* Parámetros financieros */}
      <div>
        <Label>Parámetros de inversión</Label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
          <Field
            label="Ticket por unidad (MXN)"
            value={ticketInput}
            onChange={e => handleTicket(e.target.value)}
            prefix="$"
          />
          <Field
            label="Vida útil del activo (años)"
            type="number"
            value={params.vida_util_anios}
            onChange={e => setParams({ ...params, vida_util_anios: Number(e.target.value) })}
            min={1} max={30}
          />
          <Field
            label="Tasa de descuento (%)"
            type="number"
            value={(params.tasa_descuento * 100).toFixed(0)}
            onChange={e => setParams({ ...params, tasa_descuento: Number(e.target.value) / 100 })}
            min={1} max={50}
            suffix="%"
          />
          <Field
            label="Unidades objetivo"
            type="number"
            value={params.n_unidades_objetivo}
            onChange={e => setParams({ ...params, n_unidades_objetivo: Number(e.target.value) })}
            min={1} max={100}
          />
        </div>
      </div>

      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

      {/* Botones */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* Demo instantáneo */}
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
          {isLoading ? (
            <><Spinner /> Procesando…</>
          ) : (
            <>⚡ Cargar Demo CDMX</>
          )}
        </button>

        {/* Análisis personalizado */}
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

      {/* Modo indicator */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '6px 10px', borderRadius: 8,
        background: 'rgba(29,158,117,0.1)', border: '1px solid rgba(29,158,117,0.25)',
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#1D9E75', flexShrink: 0 }} />
        <span style={{ fontSize: 11, color: '#1D9E75' }}>Modo Demo — IBM Watsonx fallback</span>
      </div>

      {/* IBM badge */}
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

function Label({ children }) {
  return (
    <div style={{ fontSize: 11, fontWeight: 600, color: '#8b91a8', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
      {children}
    </div>
  )
}

function Field({ label, value, onChange, type = 'text', prefix, suffix, min, max }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: '#8b91a8', marginBottom: 4 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
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
        {suffix && <span style={{ fontSize: 12, color: '#8b91a8' }}>{suffix}</span>}
      </div>
    </div>
  )
}

function Spinner() {
  return (
    <div style={{
      width: 14, height: 14, borderRadius: '50%',
      border: '2px solid rgba(255,255,255,0.2)',
      borderTopColor: '#e8eaf0',
      animation: 'spin 0.7s linear infinite',
    }} />
  )
}
