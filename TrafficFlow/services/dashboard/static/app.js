const mapa = L.map('map').setView([53.5, -2.2], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18,
  attribution: '&copy; OpenStreetMap contributors',
}).addTo(mapa);

const marcadores = new Map();
const historico = [];
const MAX_HISTORICO = 200;

const tabla = document.getElementById('tabla-eventos');
const contador = document.getElementById('contador-eventos');
const velocidadMedia = document.getElementById('velocidad-media');
const congestionDominante = document.getElementById('congestion-dominante');

function colorSegunCongestion(nivel) {
  switch (nivel) {
    case 'baja':
      return 'congestion-baja';
    case 'media':
      return 'congestion-media';
    case 'alta':
      return 'congestion-alta';
    case 'critica':
      return 'congestion-critica';
    default:
      return 'congestion-baja';
  }
}

function actualizarIndicadores() {
  if (!historico.length) {
    contador.textContent = '0';
    velocidadMedia.textContent = '0 km/h';
    congestionDominante.textContent = '-';
    return;
  }

  contador.textContent = historico.length.toString();
  const velocidadPromedio = historico.reduce((acc, item) => acc + (item.average_speed_kph || 0), 0) / historico.length;
  velocidadMedia.textContent = `${velocidadPromedio.toFixed(1)} km/h`;
  const conteoCongestion = historico.reduce((acc, item) => {
    const nivel = item.congestion_level || 'desconocido';
    acc[nivel] = (acc[nivel] || 0) + 1;
    return acc;
  }, {});
  const dominante = Object.entries(conteoCongestion).sort((a, b) => b[1] - a[1])[0]?.[0] || '-';
  congestionDominante.textContent = dominante;
}

function actualizarTabla(evento) {
  const fila = document.createElement('tr');
  fila.innerHTML = `
    <td>${evento.sensor_id || '-'}</td>
    <td>${evento.receiver_id || '-'}</td>
    <td>${evento.local_authority || '-'}</td>
    <td><span class="badge ${colorSegunCongestion(evento.congestion_level)}">${evento.congestion_level}</span></td>
    <td>${(evento.average_speed_kph || 0).toFixed(1)} km/h</td>
    <td>${evento.total_vehicles ?? 0}</td>
  `;
  tabla.prepend(fila);
  while (tabla.children.length > MAX_HISTORICO) {
    tabla.removeChild(tabla.lastChild);
  }
}

function actualizarMapa(evento) {
  if (typeof evento.latitude !== 'number' || typeof evento.longitude !== 'number') {
    return;
  }
  const clave = `${evento.sensor_id}-${evento.receiver_id}`;
  const contenidoPopup = `
    <strong>${evento.local_authority || 'Autoridad desconocida'}</strong><br/>
    Sensor: ${evento.sensor_id || '-'}<br/>
    Receptor: ${evento.receiver_id || '-'}<br/>
    Congestión: ${evento.congestion_level || '-'}<br/>
    Velocidad: ${(evento.average_speed_kph || 0).toFixed(1)} km/h<br/>
    Vehículos: ${evento.total_vehicles ?? 0}
  `;
  const estilo = {
    color: '#1d4ed8',
    fillColor: '#38bdf8',
    fillOpacity: 0.7,
    radius: Math.min(18, 6 + (evento.total_vehicles || 0) / 150),
  };

  let marcador = marcadores.get(clave);
  if (!marcador) {
    marcador = L.circleMarker([evento.latitude, evento.longitude], estilo).addTo(mapa);
    marcadores.set(clave, marcador);
  }
  marcador.setLatLng([evento.latitude, evento.longitude]);
  marcador.setStyle(estilo);
  marcador.bindPopup(contenidoPopup);
}

function registrarEvento(evento) {
  historico.unshift(evento);
  if (historico.length > MAX_HISTORICO) {
    historico.pop();
  }
  actualizarIndicadores();
  actualizarTabla(evento);
  actualizarMapa(evento);
}

function conectar() {
  const protocolo = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${protocolo}://${window.location.host}/stream`);

  ws.onmessage = (mensaje) => {
    try {
      const evento = JSON.parse(mensaje.data);
      registrarEvento(evento);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('No se pudo parsear el evento entrante', error);
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
