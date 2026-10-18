function readTextValue(value) {
  if (value === null || typeof value === 'undefined') return '—';
  if (typeof value === 'string') return value.trim() || '—';
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    if (!value.length) return '—';
    return value.map((entry) => readTextValue(entry)).filter((text) => text && text !== '—').join('; ');
  }
  if (typeof value === 'object') {
    const preferredKeys = ['descripcion', 'nombre', 'razon_social', 'folio', 'numero_factura', 'numero_guia', 'talla', 'estado', 'observacion'];
    for (const key of preferredKeys) {
      if (value[key] !== undefined && value[key] !== null && value[key] !== '') {
        return readTextValue(value[key]);
      }
    }
    const otherKeys = Object.keys(value).filter((key) => value[key] !== undefined && value[key] !== null && value[key] !== '');
    if (!otherKeys.length) return '—';
    return otherKeys.map((key) => `${key}: ${readTextValue(value[key])}`).join('; ');
  }
  return String(value);
}

function renderReportTable(inputId, containerId, cellFormatter) {
  const input = document.getElementById(inputId);
  const container = document.getElementById(containerId);
  if (!input || !container || !input.value) return;

  let rows = [];
  try {
    rows = JSON.parse(input.value);
  } catch (error) {
    return;
  }

  if (!Array.isArray(rows)) rows = [rows];
  if (!rows.length) return;

  const safeRows = rows.filter((row) => row && typeof row === 'object');
  if (!safeRows.length) return;

  const headers = Array.from(new Set(safeRows.flatMap((row) => Object.keys(row))));
  const table = document.createElement('table');
  table.className = 'table table-striped';
  const thead = document.createElement('thead');
  const tbody = document.createElement('tbody');
  const headerRow = document.createElement('tr');

  headers.forEach((key) => {
    const th = document.createElement('th');
    th.textContent = key.replace(/_/g, ' ');
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);

  const formatter = typeof cellFormatter === 'function'
    ? cellFormatter
    : (key, row) => readTextValue(row[key]);

  safeRows.forEach((row) => {
    const tr = document.createElement('tr');
    headers.forEach((key) => {
      const td = document.createElement('td');
      td.textContent = formatter(key, row);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  container.innerHTML = '';
  container.appendChild(table);
}

function renderStructuredTable(rows, containerId) {
  const container = document.getElementById(containerId);
  if (!container || !Array.isArray(rows) || !rows.length) return;

  const safeRows = rows.filter((row) => row && typeof row === 'object');
  if (!safeRows.length) return;

  const headers = Array.from(new Set(safeRows.flatMap((row) => Object.keys(row))));
  const table = document.createElement('table');
  table.className = 'table table-striped';
  const thead = document.createElement('thead');
  const tbody = document.createElement('tbody');
  const headerRow = document.createElement('tr');

  headers.forEach((key) => {
    const th = document.createElement('th');
    th.textContent = key.replace(/_/g, ' ');
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);

  safeRows.forEach((row) => {
    const tr = document.createElement('tr');
    headers.forEach((key) => {
      const td = document.createElement('td');
      td.textContent = readTextValue(row[key]);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  container.innerHTML = '';
  container.appendChild(table);
}

function buildCatalogMap(rows, idKey, labelKeys) {
  const map = new Map();
  (rows || []).forEach((row) => {
    if (!row || row[idKey] === undefined || row[idKey] === null || row[idKey] === '') return;
    const numeric = Number(row[idKey]);
    if (Number.isNaN(numeric)) return;
    const label = (Array.isArray(labelKeys) ? labelKeys : [labelKeys]).map((key) => row[key]).find((value) => value !== undefined && value !== null && String(value).trim() !== '');
    map.set(numeric, label !== undefined ? String(label) : `Sin descripción (ID: ${numeric})`);
  });
  return map;
}

function resolveCatalogLabel(value, catalogMap, fallbackLabel) {
  if (value === null || typeof value === 'undefined') return '—';
  const numeric = Number(value);
  if (!Number.isNaN(numeric) && catalogMap && catalogMap.has(numeric)) {
    return catalogMap.get(numeric);
  }
  if (typeof value === 'object') {
    const nested = value.descripcion || value.nombre || value.razon_social || value.folio || value.numero_factura || value.numero_guia;
    if (nested !== undefined && nested !== null && String(nested).trim() !== '') {
      return String(nested);
    }
    return fallbackLabel || '—';
  }
  const text = String(value).trim();
  return text || fallbackLabel || '—';
}

function flattenPedidoDetails(rows, options) {
  const clientesMap = buildCatalogMap(options.clientes || [], 'id_cliente', ['nombre', 'razon_social']);
  const vendedoresMap = buildCatalogMap(options.vendedores || [], 'id_vendedor', ['nombre']);
  const productosMap = buildCatalogMap(options.productos || [], 'id_variante', ['descripcion']);

  const flattened = [];
  (rows || []).forEach((row) => {
    const pedidoInfo = row && typeof row === 'object' ? (row.pedidos || row) : {};
    const pedidoId = row?.id_pedido ?? pedidoInfo?.id_pedido ?? '—';
    const clienteId = pedidoInfo?.cliente_asociado ?? row?.cliente_asociado;
    const vendedorId = pedidoInfo?.vendedor_asociado ?? row?.vendedor_asociado;
    const detalle = Array.isArray(row?.detalle_pedidos) ? row.detalle_pedidos : [];

    if (!detalle.length) {
      flattened.push({
        Pedido: pedidoId,
        Cliente: resolveCatalogLabel(clienteId, clientesMap, 'Sin nombre'),
        Vendedor: resolveCatalogLabel(vendedorId, vendedoresMap, 'Sin nombre'),
        Producto: 'Sin detalle',
        Cantidad: '—',
      });
      return;
    }

    detalle.forEach((item) => {
      const productId = item?.id_variante ?? item?.producto_variantes?.id_variante ?? item?.id_producto;
      const productLabel = item?.producto_variantes?.descripcion || resolveCatalogLabel(productId, productosMap, 'Sin descripción');
      flattened.push({
        Pedido: pedidoId,
        Cliente: resolveCatalogLabel(clienteId, clientesMap, 'Sin nombre'),
        Vendedor: resolveCatalogLabel(vendedorId, vendedoresMap, 'Sin nombre'),
        Producto: productLabel,
        Cantidad: item?.cantidad ?? '—',
      });
    });
  });

  return flattened;
}

function flattenDespachoRows(rows, options) {
  const clientesMap = buildCatalogMap(options.clientes || [], 'id_cliente', ['nombre', 'razon_social']);
  const vendedoresMap = buildCatalogMap(options.vendedores || [], 'id_vendedor', ['nombre']);
  const productosMap = buildCatalogMap(options.productos || [], 'id_variante', ['descripcion']);

  return (rows || []).map((row) => {
    const pedidoInfo = row?.pedidos || {};
    const pedidoId = row?.id_pedido ?? pedidoInfo?.id_pedido ?? '—';
    const clienteId = pedidoInfo?.cliente_asociado ?? row?.cliente_asociado;
    const vendedorId = pedidoInfo?.vendedor_asociado ?? row?.vendedor_asociado;
    const details = Array.isArray(row?.detalle_pedidos) ? row.detalle_pedidos : [];
    const products = details.map((item) => {
      const productId = item?.id_variante ?? item?.producto_variantes?.id_variante ?? item?.id_producto;
      const productLabel = item?.producto_variantes?.descripcion || resolveCatalogLabel(productId, productosMap, 'Sin descripción');
      const quantity = item?.cantidad;
      return quantity !== undefined && quantity !== null && quantity !== '' ? `${productLabel} (${quantity})` : productLabel;
    });

    return {
      'ID despacho': row?.id_despacho ?? '—',
      'Número guía': row?.numero_guia ?? '—',
      'Fecha': row?.fecha ?? '—',
      'Estado': row?.estado ?? '—',
      'Cliente asociado': resolveCatalogLabel(clienteId, clientesMap, 'Sin nombre'),
      'Pedido': pedidoId,
      'Vendedor asociado': resolveCatalogLabel(vendedorId, vendedoresMap, 'Sin nombre'),
      'Factura': row?.facturas?.numero_factura ?? row?.numero_factura ?? row?.id_factura ?? '—',
      'Productos': products.length ? products.join('; ') : '—',
      'Observación': row?.observacion ?? '—',
    };
  });
}

function flattenFacturaClienteRows(rows, options) {
  const clientesMap = buildCatalogMap(options.clientes || [], 'id_cliente', ['nombre', 'razon_social']);
  const vendedoresMap = buildCatalogMap(options.vendedores || [], 'id_vendedor', ['nombre']);

  return (rows || []).map((row) => {
    const pedidoInfo = row?.pedidos || {};
    const clienteId = pedidoInfo?.cliente_asociado ?? row?.cliente_asociado;
    const vendedorId = pedidoInfo?.vendedor_asociado ?? row?.vendedor_asociado;
    const facturasInfo = row?.facturas || {};

    return {
      'Cliente asociado': resolveCatalogLabel(clienteId, clientesMap, 'Sin nombre'),
      'Pedido': row?.id_pedido ?? pedidoInfo?.id_pedido ?? '—',
      'Vendedor asociado': resolveCatalogLabel(vendedorId, vendedoresMap, 'Sin nombre'),
      'Factura': facturasInfo?.numero_factura ?? row?.numero_factura ?? row?.id_factura ?? '—',
      'Número guía': row?.numero_guia ?? '—',
      'Fecha': row?.fecha ?? '—',
      'Estado': row?.estado ?? '—',
      'Observación': row?.observacion ?? '—',
    };
  });
}
