from dataclasses import dataclass


CLAVES_AUTOINCREMENTALES = {'roles': 'id_rol', 'usuarios': 'id_usuario'}


@dataclass
class RespuestaFalsa:
    data: list


class ConsultaFalsa:
    def __init__(self, tablas, nombre):
        self.tablas = tablas
        self.nombre = nombre
        self.filtros = []
        self.operacion = 'select'
        self.valores = None
        self.orden = None
        self.limite = None

    def select(self, columnas='*'):
        return self

    def eq(self, columna, valor):
        self.filtros.append((columna, valor))
        return self

    def order(self, columna, desc=False):
        self.orden = (columna, desc)
        return self

    def limit(self, cantidad):
        self.limite = cantidad
        return self

    def insert(self, valores):
        self.operacion, self.valores = 'insert', valores
        return self

    def update(self, valores):
        self.operacion, self.valores = 'update', valores
        return self

    def delete(self):
        self.operacion = 'delete'
        return self

    def _cumple_filtros(self, fila):
        return all(str(fila.get(columna)) == str(valor) for columna, valor in self.filtros)

    def execute(self):
        filas = self.tablas.setdefault(self.nombre, [])
        if self.operacion == 'insert':
            nuevas = self.valores if isinstance(self.valores, list) else [self.valores]
            # Simula la clave primaria autoincremental de las tablas que la tienen.
            clave = CLAVES_AUTOINCREMENTALES.get(self.nombre)
            for nueva in nuevas:
                nueva = dict(nueva)
                if clave:
                    nueva.setdefault(clave, max([f.get(clave) or 0 for f in filas], default=0) + 1)
                filas.append(nueva)
            return RespuestaFalsa([dict(f) for f in filas[-len(nuevas):]])
        coincidentes = [fila for fila in filas if self._cumple_filtros(fila)]
        if self.operacion == 'update':
            for fila in coincidentes:
                fila.update(self.valores)
        elif self.operacion == 'delete':
            self.tablas[self.nombre] = [fila for fila in filas if fila not in coincidentes]
        if self.orden:
            columna, desc = self.orden
            coincidentes = sorted(coincidentes, key=lambda fila: str(fila.get(columna)), reverse=desc)
        if self.limite is not None:
            coincidentes = coincidentes[:self.limite]
        return RespuestaFalsa([dict(fila) for fila in coincidentes])


class SupabaseFalso:
    def __init__(self, tablas=None):
        self.tablas = tablas or {}

    def table(self, nombre):
        return ConsultaFalsa(self.tablas, nombre)
