"""Dibujo de códigos de barras EAN-13 en SVG, sin librerías externas.

El número lo arma la base de datos (fn_generar_ean); aquí solo se dibuja.
"""

_CODIGOS_L = ["0001101", "0011001", "0010011", "0111101", "0100011",
              "0110001", "0101111", "0111011", "0110111", "0001011"]
_CODIGOS_G = ["0100111", "0110011", "0011011", "0100001", "0011101",
              "0111001", "0000101", "0010001", "0001001", "0010111"]
_CODIGOS_R = ["1110010", "1100110", "1101100", "1000010", "1011100",
              "1001110", "1010000", "1000100", "1001000", "1110100"]
# El primer dígito no se dibuja: define si cada dígito de la izquierda va con L o G.
_PARIDAD = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
            "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"]

# Posiciones (en módulos) de las barras de guarda, que se dibujan más largas.
_GUARDAS = set(range(0, 3)) | set(range(45, 50)) | set(range(92, 95))


def digito_verificador(codigo12):
    suma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(codigo12))
    return str((10 - suma % 10) % 10)


def modulos(codigo):
    """Devuelve los 95 módulos (1 = barra, 0 = espacio) de un EAN-13."""
    if len(codigo) != 13 or not codigo.isdigit():
        raise ValueError(f"El código EAN debe tener 13 dígitos: {codigo!r}")
    paridad = _PARIDAD[int(codigo[0])]
    izquierda = "".join(
        (_CODIGOS_L if paridad[i] == "L" else _CODIGOS_G)[int(d)]
        for i, d in enumerate(codigo[1:7])
    )
    derecha = "".join(_CODIGOS_R[int(d)] for d in codigo[7:13])
    return "101" + izquierda + "01010" + derecha + "101"


def svg(codigo, alto=40, alto_guardas=46):
    """SVG del código de barras (sin texto; los números se escriben en HTML).

    Las unidades son módulos, así que el ancho real lo define el CSS.
    """
    barras = modulos(codigo)
    rects = []
    x = 0
    while x < len(barras):
        if barras[x] == "1":
            inicio = x
            while x < len(barras) and barras[x] == "1":
                x += 1
            h = alto_guardas if inicio in _GUARDAS else alto
            rects.append(f'<rect x="{inicio}" y="0" width="{x - inicio}" height="{h}"/>')
        else:
            x += 1
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 95 {alto_guardas}" '
        f'preserveAspectRatio="none" shape-rendering="crispEdges">'
        f'{"".join(rects)}</svg>'
    )
