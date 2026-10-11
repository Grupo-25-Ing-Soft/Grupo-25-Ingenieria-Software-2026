const mongoose = require('mongoose');

const productoSchema = new mongoose.Schema({
  codigo: {
    type: String,
    required: true,
    unique: true
  },
  nombre: {
    type: String,
    required: true
  },
  descripcion: {
    type: String
  },
  categoria: {
    type: String
  },
  precio_venta: {
    type: Number,
    required: true
  },
  stock: {
    type: Number,
    default: 0
  },
  color: {
    type: String
  },
  talla: {
    type: String
  },
  estado: {
    type: String,
    default: 'activo'
  }
}, {
  timestamps: true
});

module.exports = mongoose.model('Producto', productoSchema);