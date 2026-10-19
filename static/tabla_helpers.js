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

// Botones Editar / Eliminar de cada fila. Abren los modales del CRUD
// (#actualizarModal y #borrarModal) con sus campos ya llenos: "valores" mapea el
// atributo name de cada campo a su valor. "registro" es el nombre que se muestra
// en la confirmación de borrado (RNF-007), en los elementos con data-registro.
function celdaAcciones(valoresEditar, valoresBorrar, registro) {
  const td = document.createElement('td');
  td.className = 'text-end text-nowrap';
  if (valoresEditar) td.appendChild(botonAccion('#actualizarModal', valoresEditar, registro, 'bi-pencil-square', 'Editar', 'btn-outline-secondary'));
  if (valoresBorrar) td.appendChild(botonAccion('#borrarModal', valoresBorrar, registro, 'bi-trash3', 'Eliminar', 'btn-outline-danger'));
  return td;
}

function botonAccion(modal, valores, registro, icono, titulo, clase) {
  const boton = document.createElement('button');
  boton.type = 'button';
  boton.className = `btn btn-sm ${clase} ms-1`;
  boton.title = titulo;
  boton.setAttribute('aria-label', `${titulo} ${registro || ''}`.trim());
  boton.dataset.modal = modal;
  boton.dataset.valores = JSON.stringify(valores);
  boton.dataset.registro = registro || '';
  boton.innerHTML = `<i class="bi ${icono}" aria-hidden="true"></i>`;
  return boton;
}

// Sirve también para botones escritos en la plantilla con data-modal y data-valores.
document.addEventListener('click', function (evento) {
  const boton = evento.target.closest('[data-modal][data-valores]');
  if (!boton) return;
  const modal = document.querySelector(boton.dataset.modal);
  if (!modal) return;
  const valores = JSON.parse(boton.dataset.valores || '{}');
  Object.entries(valores).forEach(([nombre, valor]) => {
    modal.querySelectorAll(`[name="${nombre}"]`).forEach((campo) => {
      if (campo.type === 'checkbox') campo.checked = Boolean(valor);
      else campo.value = (valor === null || typeof valor === 'undefined') ? '' : valor;
    });
  });
  modal.querySelectorAll('[data-registro]').forEach((elemento) => { elemento.textContent = boton.dataset.registro; });
  bootstrap.Modal.getOrCreateInstance(modal).show();
});
