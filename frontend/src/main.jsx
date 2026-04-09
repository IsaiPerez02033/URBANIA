// Importamos React como base del sistema de componentes
import React from 'react'
// Importamos ReactDOM para montar la aplicación en el DOM del navegador
import ReactDOM from 'react-dom/client'
// Importamos el componente raíz de la aplicación
import App from './App'
// Importamos los estilos base de Leaflet para el mapa interactivo
import 'leaflet/dist/leaflet.css'
// Importamos los estilos globales de la aplicación
import './index.css'

// Montamos la aplicación en el elemento con id "root" definido en index.html
ReactDOM.createRoot(document.getElementById('root')).render(
  // StrictMode activa advertencias adicionales en desarrollo para detectar problemas potenciales
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
