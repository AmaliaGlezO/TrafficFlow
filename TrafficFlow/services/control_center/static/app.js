const tabla = document.getElementById('tabla-estado');
const estadisticas = document.getElementById('estadisticas');

const estados = new Map();

function formatearFecha(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function renderizarTabla() {
  const filas = Array.from(estados.values())
    .sort((a, b) => a.entity_type.localeCompare(b.entity_type) || a.entity_id.localeCompare(b.entity_id))
    .map((estado) => `
      <tr>
        <td>${estado.entity_type}</td>
        <td>${estado.entity_id}</td>
        <td><span class="badge ${estado.status}">${estado.status}</span></td>
        <td>${formatearFecha(estado.last_seen_iso)}</td>
        <td>
          <div class="metricas">
            ${Object.entries(estado.metrics || {})
              .map(([clave, valor]) => `<span>${clave}: <strong>${valor}</strong></span>`)
              .join('')}
          </div>
        </td>
      </tr>
    `)
    .join('');
  tabla.innerHTML = filas || '<tr><td colspan="5">Esperando telemetría...</td></tr>';
}

function renderizarEstadisticas() {
  const resumen = {};
  estados.forEach((estado) => {
    resumen[estado.entity_type] = (resumen[estado.entity_type] || 0) + 1;
  });
  const total = estados.size;
  estadisticas.innerHTML = `
    <div class="card">
      <h2>Componentes activos</h2>
      <span>${total}</span>
    </div>
    ${Object.entries(resumen)
      .map(
        ([tipo, cantidad]) => `
          <div class="card">
            <h2>${tipo}</h2>
            <span>${cantidad}</span>
          </div>
        `,
      )
      .join('')}
  `;
}

function manejarMensaje({ type, payload }) {
  if (type === 'snapshot' && Array.isArray(payload)) {
    estados.clear();
    payload.forEach((item) => estados.set(`${item.entity_type}::${item.entity_id}`, item));
  } else if (type === 'update' && payload) {
    estados.set(`${payload.entity_type}::${payload.entity_id}`, payload);
  } else if (type === 'expired' && payload) {
    estados.delete(`${payload.entity_type}::${payload.entity_id}`);
  }
  renderizarEstadisticas();
  renderizarTabla();
}

function conectar() {
  const protocolo = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${protocolo}://${window.location.host}/telemetria`);

  ws.onmessage = (mensaje) => {
    try {
      const datos = JSON.parse(mensaje.data);
      manejarMensaje(datos);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error decodificando telemetría', error);
    }
  };

  ws.onclose = () => {
    setTimeout(conectar, 3000);
  };

  ws.onerror = () => {
    ws.close();
  };
}

conectar();
renderizarEstadisticas();
renderizarTabla();
