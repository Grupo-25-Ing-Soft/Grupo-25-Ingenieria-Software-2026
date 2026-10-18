// Formato compartido de las tablas de mantención (no se usa en los informes).

// Deja la columna del nombre ("nombre" por defecto) como la primera, si existe.
function ordenarColumnasTabla(headers, primera = 'nombre') {
  if (!headers.includes(primera)) return headers;
  return [primera, ...headers.filter((key) => key !== primera)];
}

// Agrega el símbolo % a las columnas de porcentaje (porcentaje_comision, descuento_porcentaje, etc.).
function formatearCeldaTabla(key, text) {
  const vacio = text === null || typeof text === 'undefined' || text === '' || text === 'null';
  if (!vacio && /porcentaje/i.test(key)) return `${text}%`;
  return text;
}
