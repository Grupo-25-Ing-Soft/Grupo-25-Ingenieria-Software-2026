// Botones con data-modal y data-valores: abren el modal indicado con sus campos ya llenos.
// "data-valores" mapea el atributo name de cada campo a su valor; "data-registro" es el
// nombre que se muestra en la confirmación (RNF-007), en los elementos con data-registro.
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
