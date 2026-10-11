const express = require('express');
const router = express.Router();
const Producto = require('../models/Producto');

// Obtener todos los productos
router.get('/', async (req, res) => {
  try {
    const productos = await Producto.find();
    res.json(productos);
  } catch (error) {
    res.status(500).json({
      mensaje: 'Error al obtener productos',
      error: error.message
    });
  }
});

// Crear producto
router.post('/', async (req, res) => {
  try {
    const nuevoProducto = new Producto(req.body);
    const productoGuardado = await nuevoProducto.save();

    res.status(201).json(productoGuardado);
  } catch (error) {
    res.status(400).json({
      mensaje: 'Error al crear producto',
      error: error.message
    });
  }
});

// Obtener producto por ID
router.get('/:id', async (req, res) => {
  try {
    const producto = await Producto.findById(req.params.id);

    if (!producto) {
      return res.status(404).json({
        mensaje: 'Producto no encontrado'
      });
    }

    res.json(producto);
  } catch (error) {
    res.status(500).json({
      mensaje: 'Error al buscar producto',
      error: error.message
    });
  }
});

// Actualizar producto
router.put('/:id', async (req, res) => {
  try {
    const productoActualizado = await Producto.findByIdAndUpdate(
      req.params.id,
      req.body,
      { new: true }
    );

    if (!productoActualizado) {
      return res.status(404).json({
        mensaje: 'Producto no encontrado'
      });
    }

    res.json(productoActualizado);
  } catch (error) {
    res.status(400).json({
      mensaje: 'Error al actualizar producto',
      error: error.message
    });
  }
});

// Eliminar producto
router.delete('/:id', async (req, res) => {
  try {
    const productoEliminado = await Producto.findByIdAndDelete(req.params.id);

    if (!productoEliminado) {
      return res.status(404).json({
        mensaje: 'Producto no encontrado'
      });
    }

    res.json({
      mensaje: 'Producto eliminado correctamente'
    });
  } catch (error) {
    res.status(500).json({
      mensaje: 'Error al eliminar producto',
      error: error.message
    });
  }
});

module.exports = router;