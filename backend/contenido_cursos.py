"""Cursos preinstalados del sistema.

Estructura estilo plataforma de cursos: cada curso tiene MODULOS y cada
modulo tiene TEMAS que el alumno recorre en orden. Cada tema trae bloques de
contenido (explicacion, ejemplo, tip, tabla, error comun), a veces una
practica interactiva, y un quiz para desbloquear el siguiente.

Los bloques de contenido usan estos tipos:
  texto     - parrafo explicativo
  ejemplo   - caso concreto con numeros
  tip       - consejo practico destacado
  ojo       - error comun que hay que evitar
  tabla     - filas de datos
  formula   - formula destacada
  video     - marcador de video (simulado)
"""

# ═══════════════════════════════════════════════════════════════════
#  CURSO 1 · CONTABILIDAD Y FINANZAS PARA LA VIDA REAL
# ═══════════════════════════════════════════════════════════════════

CONTABILIDAD = {
    "slug": "contabilidad",
    "titulo": "Contabilidad y Finanzas para la Vida Real",
    "descripcion": (
        "Aprende a manejar el dinero de un negocio de verdad: desde anotar tu primera venta "
        "hasta presentar una declaracion ante la DIAN. Al terminar vas a poder llevar la "
        "contabilidad de una tienda, una finca o tu propio emprendimiento, y vas a entender "
        "los numeros de cualquier empresa."
    ),
    "categoria": "Emprendimiento y finanzas",
    "icono": "🧮",
    "color": "#0E7C86",
    "duracion_texto": "14 horas",
    "grado_sugerido": "8-11",
    "modulos": [
        # ─────────── MODULO 1 ───────────
        {
            "titulo": "Los cimientos: el dinero y sus reglas",
            "descripcion": "Antes de tocar un numero, entiende de que se trata todo esto.",
            "nivel": "basico", "icono": "🌱",
            "temas": [
                {
                    "titulo": "¿Por que existe la contabilidad?",
                    "resumen": "La historia de por que los humanos empezamos a anotar el dinero.",
                    "duracion_min": 10,
                    "contenido": [
                        {"t": "texto", "h": "Un problema de hace 7.000 anos",
                         "p": "Imagina que eres un comerciante en Mesopotamia. Le fias 20 sacos de trigo a un vecino, le compras 3 ovejas a otro, y le debes cebada a un tercero. A los dos meses, ¿como te acuerdas de todo? Ese fue el problema. Las primeras tablillas de arcilla con marcas no eran poesia: eran contabilidad. Anotar fue lo que permitio que el comercio creciera mas alla de lo que una persona puede recordar."},
                        {"t": "texto", "h": "El invento que lo cambio todo",
                         "p": "En 1494, un fraile italiano llamado Luca Pacioli publico un libro donde explicaba un metodo que ya usaban los mercaderes de Venecia: la partida doble. La idea es simple pero poderosa: todo movimiento de dinero tiene DOS caras. Si compras mercancia con efectivo, tu mercancia sube y tu efectivo baja. Siempre hay un origen y un destino."},
                        {"t": "ejemplo", "h": "Partida doble en tu vida",
                         "p": "Compras un celular de $800.000 con tus ahorros. Dos cosas pasan al tiempo: (1) tienes un celular que vale $800.000, (2) tienes $800.000 menos en efectivo. Tu riqueza total no cambio: cambio de forma. Eso es partida doble."},
                        {"t": "tip", "h": "Por que te sirve aunque no seas contador",
                         "p": "Quien entiende contabilidad entiende si un negocio esta ganando o solo aparentando. Muchos negocios quiebran vendiendo mucho, porque nunca supieron cuanto les costaba realmente vender."},
                    ],
                    "quiz": [
                        {"q": "Segun la partida doble, cuando compras mercancia con efectivo:",
                         "op": ["Solo baja el efectivo", "Sube la mercancia y baja el efectivo", "Solo sube la mercancia"],
                         "correcta": 1,
                         "explica": "Todo movimiento tiene dos caras: algo entra y algo sale. Tu riqueza cambio de forma, no de tamano."},
                        {"q": "¿Para que nacio la contabilidad?",
                         "op": ["Para pagar impuestos", "Para recordar deudas y cuentas del comercio", "Para hacer graficas"],
                         "correcta": 1,
                         "explica": "Nacio del problema practico de no poder recordar todas las cuentas de memoria."},
                    ],
                },
                {
                    "titulo": "Las 5 palabras que lo explican todo",
                    "resumen": "Activo, pasivo, patrimonio, ingreso y gasto. Con esto entiendes cualquier empresa.",
                    "duracion_min": 14,
                    "contenido": [
                        {"t": "texto", "h": "Vocabulario minimo",
                         "p": "Toda la contabilidad del mundo se construye con cinco palabras. Si las entiendes bien, puedes leer los estados financieros de una tienda de barrio o de Ecopetrol. Son las mismas."},
                        {"t": "tabla", "h": "Las 5 palabras",
                         "filas": [
                             ["ACTIVO", "Lo que TIENES", "Efectivo, mercancia, un local, una moto, lo que te deben"],
                             ["PASIVO", "Lo que DEBES", "Prestamos, facturas por pagar, impuestos pendientes"],
                             ["PATRIMONIO", "Lo que es TUYO de verdad", "Activo menos pasivo. Tu riqueza real"],
                             ["INGRESO", "Dinero que ENTRA por vender", "Ventas del dia, servicios prestados"],
                             ["GASTO", "Dinero que SALE para operar", "Arriendo, sueldos, servicios publicos"],
                         ]},
                        {"t": "formula", "h": "La ecuacion de oro",
                         "p": "ACTIVO = PASIVO + PATRIMONIO"},
                        {"t": "ejemplo", "h": "La tienda de Dona Rosa",
                         "p": "Dona Rosa tiene: mercancia por $3.000.000, efectivo en caja $500.000 y una nevera que vale $1.500.000. Total ACTIVO = $5.000.000. Le debe $1.200.000 al proveedor. Total PASIVO = $1.200.000. Entonces su PATRIMONIO es $5.000.000 - $1.200.000 = $3.800.000. Eso es lo que realmente es de ella."},
                        {"t": "ojo", "h": "El error mas comun",
                         "p": "Mucha gente cree que si vendio $10 millones, gano $10 millones. NO. Vender es ingreso; ganar es lo que queda despues de restar lo que costo la mercancia y los gastos. Un negocio puede vender muchisimo y estar perdiendo plata."},
                    ],
                    "quiz": [
                        {"q": "Tienes $8M en activos y debes $3M. ¿Cual es tu patrimonio?",
                         "op": ["$11M", "$5M", "$3M"], "correcta": 1,
                         "explica": "Patrimonio = Activo - Pasivo = 8 - 3 = $5M. Es lo que queda tuyo si pagas todo."},
                        {"q": "El arriendo del local es un:",
                         "op": ["Activo", "Gasto", "Patrimonio"], "correcta": 1,
                         "explica": "Es dinero que sale para poder operar. No te queda nada a cambio."},
                        {"q": "La mercancia que tienes en bodega es:",
                         "op": ["Un activo", "Un pasivo", "Un gasto"], "correcta": 0,
                         "explica": "Es algo que TIENES y que se puede convertir en dinero al venderlo."},
                    ],
                },
                {
                    "titulo": "Registrar ventas: tu primer libro",
                    "resumen": "Como anotar lo que vendes y saber cuanto ganaste de verdad.",
                    "duracion_min": 15,
                    "contenido": [
                        {"t": "texto", "h": "El libro que salva negocios",
                         "p": "El registro de ventas responde tres preguntas: que se vende mas, cuanto entra al dia, y cuanto estas ganando de verdad. Sin el, estas adivinando."},
                        {"t": "texto", "h": "Costo, precio y utilidad",
                         "p": "COSTO es lo que te costo el producto. PRECIO es a como lo vendes. UTILIDAD es la diferencia. El MARGEN es esa utilidad expresada en porcentaje sobre el precio de venta."},
                        {"t": "formula", "h": "Margen de ganancia",
                         "p": "Margen % = (Precio - Costo) / Precio x 100"},
                        {"t": "ejemplo", "h": "Calculando el margen",
                         "p": "Compras un cuaderno en $2.000 y lo vendes en $3.000. Utilidad = $1.000. Margen = 1.000/3.000 = 33%. Si vendes 50 cuadernos al mes, tu utilidad es $50.000. ¿Alcanza para pagar el arriendo? Esa es la pregunta que responde la contabilidad."},
                        {"t": "tip", "h": "Regla practica",
                         "p": "En un negocio pequeno, si tu margen es menor al 25% te queda muy poco para cubrir gastos. Si es mayor al 60%, revisa que tu precio siga siendo competitivo."},
                    ],
                    "quiz": [
                        {"q": "Compras en $6.000 y vendes en $10.000. ¿Cual es el margen?",
                         "op": ["40%", "60%", "66%"], "correcta": 0,
                         "explica": "Utilidad = 4.000. Margen = 4.000/10.000 = 40%."},
                        {"q": "Vendiste $5.000.000 este mes. ¿Ganaste $5.000.000?",
                         "op": ["Si", "No, hay que restar costos y gastos", "Depende del banco"],
                         "correcta": 1,
                         "explica": "Vender no es ganar. La utilidad aparece despues de restar lo que costo la mercancia y los gastos del negocio."},
                    ],
                },
            ],
        },
        # ─────────── MODULO 2 ───────────
        {
            "titulo": "El dia a dia del negocio",
            "descripcion": "Inventario, caja y los documentos que te respaldan.",
            "nivel": "basico", "icono": "📦",
            "temas": [
                {
                    "titulo": "Inventario: lo que tienes para vender",
                    "resumen": "Controla tu mercancia con fotos, cantidades y precios. Practica incluida.",
                    "duracion_min": 18, "tipo_practica": "inventario",
                    "contenido": [
                        {"t": "texto", "h": "El inventario es plata quieta",
                         "p": "Cada producto en tu bodega es dinero que ya gastaste y que todavia no has recuperado. Por eso tener demasiado inventario es tan peligroso como tener muy poco: si tienes mucho, tu plata esta dormida (y se puede danar o pasar de moda); si tienes poco, pierdes ventas."},
                        {"t": "texto", "h": "La ficha de cada producto",
                         "p": "Nombre, foto, cantidad, precio de costo y precio de venta. La foto no es un lujo: evita confusiones cuando tienes productos parecidos y sirve de prueba en un inventario fisico."},
                        {"t": "formula", "h": "Rotacion de inventario",
                         "p": "Rotacion = Unidades vendidas al mes / Unidades en bodega"},
                        {"t": "ejemplo", "h": "Producto estrella vs producto muerto",
                         "p": "Tienes 100 gaseosas y vendes 80 al mes: rotacion 0.8, excelente. Tienes 50 sombrillas y vendes 2 al mes: rotacion 0.04, tienes plata dormida por 25 meses. Esa es la senal para dejar de comprar sombrillas."},
                        {"t": "ojo", "h": "El robo hormiga",
                         "p": "Si tu inventario en papel dice 100 y al contar hay 94, esos 6 se llaman merma. Puede ser robo, dano o error de registro. Si no cuentas, nunca te enteras."},
                    ],
                    "quiz": [
                        {"q": "Tienes 60 unidades y vendes 45 al mes. ¿Como es la rotacion?",
                         "op": ["Muy baja, plata dormida", "Buena, se mueve rapido", "Imposible saber"],
                         "correcta": 1,
                         "explica": "Rotacion = 45/60 = 0.75. Se renueva casi cada mes, muy sano."},
                        {"q": "Tu registro dice 200 unidades pero al contar hay 187. Eso se llama:",
                         "op": ["Utilidad", "Merma", "Pasivo"], "correcta": 1,
                         "explica": "Merma: la diferencia entre lo que deberia haber y lo que hay. Hay que investigar por que."},
                    ],
                },
                {
                    "titulo": "Arqueo de caja: el momento de la verdad",
                    "resumen": "Al cerrar el dia, ¿cuadra tu caja? Aqui aprendes a comprobarlo.",
                    "duracion_min": 16, "tipo_practica": "arqueo",
                    "contenido": [
                        {"t": "texto", "h": "¿Que es un arqueo?",
                         "p": "Es contar fisicamente el dinero de la caja y compararlo con lo que dice tu registro. Se hace al cerrar el dia, o cuando cambia el turno del cajero. Es la forma mas simple y mas poderosa de control interno que existe."},
                        {"t": "formula", "h": "Las dos formulas del arqueo",
                         "p": "Efectivo esperado = Saldo inicial + Ventas en efectivo - Retiros\\nDiferencia = Efectivo contado - Efectivo esperado"},
                        {"t": "ejemplo", "h": "Un arqueo real",
                         "p": "Abriste con $200.000 de base. Vendiste $850.000 en efectivo. Sacaste $150.000 para pagarle al proveedor. Esperado = 200.000 + 850.000 - 150.000 = $900.000. Cuentas los billetes y hay $880.000. Falta $20.000. Ahora toca investigar: ¿un vuelto mal dado? ¿una venta no registrada?"},
                        {"t": "tip", "h": "El sobrante tambien es problema",
                         "p": "Si sobra plata, no celebres. Significa que hubo una venta que no se registro, o que le cobraste de mas a alguien. Ambas cosas son errores que hay que corregir."},
                        {"t": "ojo", "h": "Nunca mezcles",
                         "p": "El dinero del negocio y el dinero personal deben estar separados. La causa numero uno de descuadre en negocios pequenos es sacar plata de la caja 'y despues la repongo'."},
                    ],
                    "quiz": [
                        {"q": "Base $100.000, ventas efectivo $400.000, retiros $50.000. ¿Cuanto deberia haber?",
                         "op": ["$450.000", "$550.000", "$350.000"], "correcta": 0,
                         "explica": "100.000 + 400.000 - 50.000 = $450.000."},
                        {"q": "Contaste $30.000 MAS de lo esperado. Eso significa:",
                         "op": ["Ganaste mas", "Hay un error de registro que investigar", "Todo bien"],
                         "correcta": 1,
                         "explica": "Un sobrante casi siempre es una venta sin registrar o un cobro de mas. Es un error, no una ganancia."},
                    ],
                },
                {
                    "titulo": "Cotizaciones, facturas y el IVA",
                    "resumen": "Los documentos legales de una venta y como se calcula el IVA.",
                    "duracion_min": 18, "tipo_practica": "factura",
                    "contenido": [
                        {"t": "texto", "h": "Primero cotizas, despues facturas",
                         "p": "La COTIZACION es una oferta: 'esto cuesta tanto, vale por 15 dias'. No obliga a nadie. La FACTURA es el documento legal que prueba que la venta ocurrio; sirve para la DIAN, para garantias y para cobrar."},
                        {"t": "tabla", "h": "Que lleva una factura en Colombia",
                         "filas": [
                             ["Numeracion", "Consecutiva y autorizada por la DIAN"],
                             ["Fecha", "Dia de la operacion"],
                             ["Vendedor", "Nombre, NIT y direccion"],
                             ["Comprador", "Nombre y NIT o cedula"],
                             ["Detalle", "Cantidad, descripcion y valor unitario"],
                             ["Subtotal, IVA y total", "El IVA general es del 19%"],
                         ]},
                        {"t": "formula", "h": "Calculo del IVA",
                         "p": "IVA = Subtotal x 0.19\\nTotal = Subtotal + IVA"},
                        {"t": "ejemplo", "h": "Factura paso a paso",
                         "p": "Vendes 10 resmas de papel a $18.000 cada una. Subtotal = $180.000. IVA 19% = $34.200. Total a cobrar = $214.200. Ojo: esos $34.200 NO son tuyos, los estas recaudando para la DIAN."},
                        {"t": "ojo", "h": "El IVA no es ganancia",
                         "p": "El error mas caro de los negocios nuevos: gastarse el IVA recaudado. Cuando llega la fecha de declarar, no tienen con que pagar. Guarda ese dinero aparte desde el primer dia."},
                        {"t": "tip", "h": "No todo lleva IVA",
                         "p": "Algunos productos estan excluidos o exentos (varios alimentos basicos, educacion, salud). Otros tienen tarifa del 5%. Verifica siempre en que categoria esta lo que vendes."},
                    ],
                    "quiz": [
                        {"q": "Vendes $500.000 antes de IVA. ¿Cuanto cobras en total?",
                         "op": ["$595.000", "$500.000", "$519.000"], "correcta": 0,
                         "explica": "IVA = 500.000 x 0.19 = 95.000. Total = $595.000."},
                        {"q": "El IVA que recaudas en tus ventas es:",
                         "op": ["Tuyo, es ganancia", "De la DIAN, lo estas recaudando", "Del cliente"],
                         "correcta": 1,
                         "explica": "Eres un intermediario: recaudas para el Estado y despues lo declaras."},
                        {"q": "La diferencia entre cotizacion y factura es:",
                         "op": ["Ninguna", "La cotizacion es una oferta, la factura prueba la venta", "La factura es mas barata"],
                         "correcta": 1,
                         "explica": "La cotizacion propone; la factura documenta legalmente lo que ya ocurrio."},
                    ],
                },
            ],
        },
        # ─────────── MODULO 3 ───────────
        {
            "titulo": "Leer los numeros de una empresa",
            "descripcion": "Balance, estado de resultados y flujo de caja: los tres reportes clave.",
            "nivel": "medio", "icono": "📊",
            "temas": [
                {
                    "titulo": "El balance general: la foto",
                    "resumen": "Que tiene, que debe y que es suyo. Con practica para cuadrarlo.",
                    "duracion_min": 16, "tipo_practica": "balance",
                    "contenido": [
                        {"t": "texto", "h": "Una foto de un instante",
                         "p": "El balance muestra la situacion de la empresa en un dia exacto, como una fotografia. Al 31 de diciembre tienes esto, debes esto, y lo tuyo es esto. Manana cambia."},
                        {"t": "formula", "h": "Siempre, sin excepcion",
                         "p": "ACTIVO = PASIVO + PATRIMONIO"},
                        {"t": "texto", "h": "Corriente vs no corriente",
                         "p": "Los activos CORRIENTES se vuelven efectivo en menos de un ano (caja, inventario, cuentas por cobrar). Los NO CORRIENTES son de largo plazo (local, maquinaria, vehiculos). Lo mismo para los pasivos: lo que debes este ano vs lo que debes a varios anos."},
                        {"t": "ejemplo", "h": "Balance de una panaderia",
                         "p": "ACTIVO: caja $800.000 + inventario $2.200.000 + horno $6.000.000 = $9.000.000. PASIVO: proveedores $1.500.000 + credito bancario $2.500.000 = $4.000.000. PATRIMONIO = $5.000.000. Comprobacion: 9.000.000 = 4.000.000 + 5.000.000. Cuadra."},
                        {"t": "tip", "h": "Como leerlo rapido",
                         "p": "Si el pasivo es mayor que el patrimonio, la empresa se esta financiando mas con deuda que con capital propio. No es malo por si solo, pero es una senal de riesgo que hay que vigilar."},
                    ],
                    "quiz": [
                        {"q": "Activo $30M, Patrimonio $18M. ¿Cuanto debe la empresa?",
                         "op": ["$48M", "$12M", "$18M"], "correcta": 1,
                         "explica": "Pasivo = Activo - Patrimonio = 30 - 18 = $12M."},
                        {"q": "El inventario es un activo:",
                         "op": ["Corriente", "No corriente", "No es activo"], "correcta": 0,
                         "explica": "Se convierte en efectivo cuando lo vendes, normalmente en menos de un ano."},
                    ],
                },
                {
                    "titulo": "Estado de resultados: ¿gane o perdi?",
                    "resumen": "La pelicula del periodo: ingresos, costos, gastos y utilidad.",
                    "duracion_min": 15,
                    "contenido": [
                        {"t": "texto", "h": "La pelicula, no la foto",
                         "p": "Si el balance es una foto de un dia, el estado de resultados es la pelicula de todo un periodo: que paso entre enero y diciembre. Cuenta como llegaste de las ventas hasta la ganancia final."},
                        {"t": "tabla", "h": "La cascada del P y G",
                         "filas": [
                             ["Ingresos por ventas", "$50.000.000"],
                             ["(-) Costo de lo vendido", "$30.000.000"],
                             ["= Utilidad bruta", "$20.000.000"],
                             ["(-) Gastos de operacion", "$12.000.000"],
                             ["= Utilidad operacional", "$8.000.000"],
                             ["(-) Impuestos", "$2.000.000"],
                             ["= Utilidad neta", "$6.000.000"],
                         ]},
                        {"t": "texto", "h": "Costo no es lo mismo que gasto",
                         "p": "El COSTO esta pegado al producto: lo que pagaste por la mercancia que vendiste. El GASTO es lo que necesitas para operar aunque no vendas nada: arriendo, sueldos, luz. Separarlos te dice si el problema esta en tus precios o en tu estructura."},
                        {"t": "ojo", "h": "Vender mucho y perder",
                         "p": "Si tu utilidad bruta es $20M y tus gastos son $25M, perdiste $5M aunque hayas vendido $50M. Por eso hay negocios llenos de clientes que cierran."},
                    ],
                    "quiz": [
                        {"q": "Ventas $80M, costo $50M, gastos $20M. ¿Utilidad operacional?",
                         "op": ["$30M", "$10M", "$60M"], "correcta": 1,
                         "explica": "80 - 50 = 30 de utilidad bruta. 30 - 20 = $10M operacional."},
                        {"q": "El sueldo del vigilante es:",
                         "op": ["Costo del producto", "Gasto de operacion", "Activo"],
                         "correcta": 1,
                         "explica": "Lo pagas vendas o no vendas. No esta pegado a ningun producto."},
                    ],
                },
                {
                    "titulo": "Flujo de caja: por que quiebran empresas rentables",
                    "resumen": "La diferencia entre tener utilidad y tener plata en el bolsillo.",
                    "duracion_min": 14, "tipo_practica": "flujo",
                    "contenido": [
                        {"t": "texto", "h": "Utilidad en papel, caja vacia",
                         "p": "Vendiste $10.000.000 a credito a 90 dias. En tu estado de resultados aparece la utilidad. Pero el arriendo se paga este viernes y en la caja no hay nada. Esa es la trampa que quiebra empresas rentables."},
                        {"t": "formula", "h": "Flujo de caja",
                         "p": "Flujo neto = Entradas reales de dinero - Salidas reales de dinero"},
                        {"t": "ejemplo", "h": "Dos negocios, misma utilidad",
                         "p": "Negocio A vende $20M de contado. Negocio B vende $20M a 90 dias. Los dos muestran la misma utilidad. Pero A puede pagar su nomina manana y B no. La utilidad es una opinion; la caja es un hecho."},
                        {"t": "tip", "h": "La regla de oro del pequeno negocio",
                         "p": "Si le vendes a credito, negocia tambien plazo con tus proveedores. Si te pagan a 60 dias y tu pagas a 30, necesitas capital de trabajo para cubrir ese hueco."},
                    ],
                    "quiz": [
                        {"q": "Una empresa con buena utilidad puede quebrar si:",
                         "op": ["Vende mucho", "No tiene efectivo para pagar sus obligaciones", "Tiene inventario"],
                         "correcta": 1,
                         "explica": "La falta de liquidez mata empresas rentables. Utilidad y caja no son lo mismo."},
                        {"q": "Vendiste $5M a 90 dias. Hoy en tu caja entraron:",
                         "op": ["$5M", "$0", "$1.6M"], "correcta": 1,
                         "explica": "La venta se registro, pero el dinero llega en 90 dias. Hoy tu caja no cambio."},
                    ],
                },
            ],
        },
        # ─────────── MODULO 4 ───────────
        {
            "titulo": "Formalizar: impuestos y nomina",
            "descripcion": "Lo que exige la ley colombiana cuando tu negocio crece.",
            "nivel": "avanzado", "icono": "🏛️",
            "temas": [
                {
                    "titulo": "La DIAN y tu declaracion de IVA",
                    "resumen": "Como se calcula y se presenta. Con practica real.",
                    "duracion_min": 18, "tipo_practica": "declaracion",
                    "contenido": [
                        {"t": "texto", "h": "¿Que es la DIAN?",
                         "p": "La Direccion de Impuestos y Aduanas Nacionales administra los impuestos en Colombia. Todo negocio formal se inscribe en el RUT y declara segun su regimen y su actividad."},
                        {"t": "formula", "h": "IVA a pagar",
                         "p": "IVA a pagar = IVA cobrado en ventas - IVA pagado en compras"},
                        {"t": "ejemplo", "h": "Un bimestre completo",
                         "p": "Vendiste $20.000.000 y cobraste $3.800.000 de IVA. Compraste mercancia por $12.000.000 y pagaste $2.280.000 de IVA. IVA a pagar = 3.800.000 - 2.280.000 = $1.520.000. Ese es el dinero que le giras a la DIAN."},
                        {"t": "texto", "h": "Por que guardar todas las facturas",
                         "p": "Ese IVA que pagaste en tus compras solo lo puedes descontar si tienes la factura. Sin factura, pierdes el descuento y terminas pagando de mas. Las facturas de compra son plata."},
                        {"t": "ojo", "h": "Las sanciones",
                         "p": "Declarar tarde genera sancion por extemporaneidad mas intereses de mora, que crecen cada dia. Es de los errores mas caros y mas faciles de evitar: es solo una fecha en el calendario."},
                    ],
                    "quiz": [
                        {"q": "IVA cobrado $5.000.000, IVA pagado en compras $1.800.000. ¿Cuanto declaras?",
                         "op": ["$6.800.000", "$3.200.000", "$1.800.000"], "correcta": 1,
                         "explica": "5.000.000 - 1.800.000 = $3.200.000 a pagar."},
                        {"q": "Si pierdes las facturas de tus compras:",
                         "op": ["No pasa nada", "No puedes descontar ese IVA y pagas mas", "La DIAN te las repone"],
                         "correcta": 1,
                         "explica": "Sin soporte no hay descuento. Guardar facturas es guardar dinero."},
                    ],
                },
                {
                    "titulo": "Nomina: contratar bien a alguien",
                    "resumen": "Cuanto cuesta realmente un empleado en Colombia.",
                    "duracion_min": 18, "tipo_practica": "nomina",
                    "contenido": [
                        {"t": "texto", "h": "El salario no es el costo",
                         "p": "Si acuerdas un salario de $1.500.000, ese NO es tu costo. Sobre el salario hay prestaciones sociales y aportes que, sumados, agregan aproximadamente entre 45% y 55% mas."},
                        {"t": "tabla", "h": "Lo que se suma al salario",
                         "filas": [
                             ["Cesantias", "1 mes de salario al ano (8.33%)"],
                             ["Intereses de cesantias", "12% sobre las cesantias"],
                             ["Prima de servicios", "1 mes de salario al ano (8.33%)"],
                             ["Vacaciones", "15 dias habiles al ano (4.17%)"],
                             ["Salud (empleador)", "8.5% del salario"],
                             ["Pension (empleador)", "12% del salario"],
                             ["ARL", "Segun el riesgo, desde 0.522%"],
                             ["Caja de compensacion", "4%"],
                         ]},
                        {"t": "ejemplo", "h": "Costo real",
                         "p": "Salario de $1.500.000. Prestaciones y aportes suman cerca de $750.000. Tu costo real mensual es cerca de $2.250.000. Si al cotizar un trabajo solo consideras el salario, estas perdiendo plata en cada contrato."},
                        {"t": "tip", "h": "El auxilio de transporte",
                         "p": "Quien gana hasta 2 salarios minimos tiene derecho a auxilio de transporte. Se suma al pago y cuenta para prestaciones, pero no para salud ni pension."},
                    ],
                    "quiz": [
                        {"q": "Un empleado con salario de $2.000.000 te cuesta aproximadamente:",
                         "op": ["$2.000.000", "$3.000.000", "$2.100.000"], "correcta": 1,
                         "explica": "Con prestaciones y aportes (cerca del 50% mas), el costo real ronda los $3.000.000."},
                        {"q": "Las cesantias equivalen aproximadamente a:",
                         "op": ["Un mes de salario al ano", "Un dia por mes", "El 2% del salario"],
                         "correcta": 0,
                         "explica": "Un mes de salario por cada ano trabajado, o proporcional al tiempo."},
                    ],
                },
                {
                    "titulo": "Auditoria: que revisan y como pasarla",
                    "resumen": "Como dejar todo tan ordenado que cualquier revision salga bien.",
                    "duracion_min": 14,
                    "contenido": [
                        {"t": "texto", "h": "Auditar es verificar",
                         "p": "Un auditor no busca culpables: busca evidencia. Toma un movimiento al azar y pide el soporte. Si cada peso registrado tiene su factura, su comprobante y su firma, la auditoria se vuelve un tramite."},
                        {"t": "tabla", "h": "Lo que siempre piden",
                         "filas": [
                             ["Soporte de cada movimiento", "Factura, recibo o comprobante"],
                             ["Conciliacion bancaria", "Que el extracto coincida con tus libros"],
                             ["Arqueos de caja", "Con firma de quien conto"],
                             ["Inventario fisico", "Contado y comparado con el sistema"],
                             ["Trazabilidad", "De donde vino y a donde fue cada peso"],
                         ]},
                        {"t": "tip", "h": "El principio que lo resume todo",
                         "p": "Registra en el momento, no al final del mes. La memoria falla y los papeles se pierden. Un sistema ordenado se construye todos los dias, no la semana antes de la auditoria."},
                        {"t": "texto", "h": "Esto mismo aplica a tu colegio",
                         "p": "El Fondo de Servicios Educativos de una institucion se audita igual: cada contrato con su CDP, su RP, sus cotizaciones y sus soportes de pago. Es exactamente lo que hace este sistema que estas usando."},
                    ],
                    "quiz": [
                        {"q": "La mejor defensa en una auditoria es:",
                         "op": ["Explicar bien", "Tener el soporte documental de cada movimiento", "Conocer al auditor"],
                         "correcta": 1,
                         "explica": "La evidencia documental es lo unico que cuenta. Sin soporte, no existe."},
                        {"q": "Conciliacion bancaria significa:",
                         "op": ["Ir al banco", "Verificar que el extracto coincida con tus libros", "Pedir un credito"],
                         "correcta": 1,
                         "explica": "Comparar tu registro contra el extracto para detectar diferencias."},
                    ],
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════
#  CURSO 2 · EMPRENDIMIENTO: DE LA IDEA AL NEGOCIO
# ═══════════════════════════════════════════════════════════════════

EMPRENDIMIENTO = {
    "slug": "emprendimiento",
    "titulo": "Emprendimiento: de la idea al negocio",
    "descripcion": (
        "Convierte una idea en un negocio real: encuentra un problema que valga la pena "
        "resolver, calcula si el numero da, y aprende a vender. Pensado para que un joven "
        "del Sur de Bolivar pueda montar algo con lo que tiene a la mano."
    ),
    "categoria": "Emprendimiento y finanzas",
    "icono": "🚀", "color": "#7C3AED", "duracion_texto": "8 horas",
    "grado_sugerido": "9-11",
    "modulos": [
        {
            "titulo": "Encontrar la idea correcta",
            "descripcion": "Las buenas ideas no se inventan: se descubren observando problemas.",
            "nivel": "basico", "icono": "💡",
            "temas": [
                {
                    "titulo": "Un problema que valga la pena",
                    "resumen": "Por que las mejores ideas nacen de una molestia real.",
                    "duracion_min": 12,
                    "contenido": [
                        {"t": "texto", "h": "No empieces por el producto",
                         "p": "La mayoria de negocios que fracasan empezaron con 'tengo una idea genial'. Los que funcionan empezaron con 'esto es un problema y nadie lo resuelve bien'. La diferencia parece pequena pero lo cambia todo."},
                        {"t": "ejemplo", "h": "Mirando alrededor",
                         "p": "En tu vereda la gente pierde media manana viajando al pueblo a comprar algo basico. Eso es un problema real, medible y repetido. Ahi hay un negocio posible. En cambio 'una app para todo' no resuelve nada concreto."},
                        {"t": "tip", "h": "La prueba de las 3 preguntas",
                         "p": "1) ¿Le pasa a mucha gente? 2) ¿Les molesta lo suficiente? 3) ¿Estarian dispuestos a pagar por resolverlo? Si alguna respuesta es no, sigue buscando."},
                    ],
                    "quiz": [
                        {"q": "Una buena idea de negocio nace de:",
                         "op": ["Un producto novedoso", "Un problema real que le importa a la gente", "Copiar lo que funciona"],
                         "correcta": 1,
                         "explica": "El problema es el punto de partida. El producto es solo la forma de resolverlo."},
                    ],
                },
                {
                    "titulo": "¿Alguien pagaria por esto?",
                    "resumen": "Validar antes de invertir: la prueba mas barata que existe.",
                    "duracion_min": 13,
                    "contenido": [
                        {"t": "texto", "h": "Validar es preguntar bien",
                         "p": "Antes de invertir tus ahorros, habla con 20 personas que tengan el problema. Pero no les preguntes '¿comprarias esto?' porque te van a decir que si por amabilidad. Preguntales que hacen HOY para resolverlo y cuanto les cuesta."},
                        {"t": "ojo", "h": "El halago no es validacion",
                         "p": "'Que buena idea' no vale nada. La unica validacion real es que alguien te de dinero, o al menos que te diga cuanto esta gastando hoy en el problema."},
                        {"t": "tip", "h": "Empieza pequeno de verdad",
                         "p": "¿Quieres montar una panaderia? Vende primero 20 panes hechos en tu casa a tus vecinos. Aprendes de costos, de gustos y de precios sin arriesgar un local."},
                    ],
                    "quiz": [
                        {"q": "La mejor forma de validar una idea es:",
                         "op": ["Preguntar si les gusta", "Ver si alguien paga o cuanto gasta hoy en el problema", "Hacer una encuesta larga"],
                         "correcta": 1,
                         "explica": "El comportamiento real vale mas que las opiniones amables."},
                    ],
                },
            ],
        },
        {
            "titulo": "Que los numeros den",
            "descripcion": "Costos, precio y punto de equilibrio.",
            "nivel": "medio", "icono": "🔢",
            "temas": [
                {
                    "titulo": "Poner precio sin regalar tu trabajo",
                    "resumen": "El error de calcular el precio solo con los materiales.",
                    "duracion_min": 15,
                    "contenido": [
                        {"t": "texto", "h": "Tu tiempo tambien cuesta",
                         "p": "El error mas comun del emprendedor nuevo: sumar solo los materiales. Si haces una torta con $20.000 de ingredientes y la vendes en $30.000, parece que ganas $10.000. Pero si te tomo 3 horas, tu trabajo valio menos que el salario minimo por hora."},
                        {"t": "formula", "h": "Precio bien calculado",
                         "p": "Precio = Materiales + Tu tiempo + Parte de los gastos fijos + Margen de ganancia"},
                        {"t": "ejemplo", "h": "La torta bien costeada",
                         "p": "Materiales $20.000 + 3 horas de trabajo a $8.000/hora = $24.000 + gas y energia $3.000 = $47.000 de costo real. Con 30% de margen: precio $61.000. Vender a $30.000 era trabajar perdiendo."},
                    ],
                    "quiz": [
                        {"q": "Al poner precio hay que incluir:",
                         "op": ["Solo los materiales", "Materiales, tu tiempo, gastos y margen", "Lo que cobre el vecino"],
                         "correcta": 1,
                         "explica": "Si no cobras tu tiempo, estas trabajando gratis y ni te enteras."},
                    ],
                },
                {
                    "titulo": "Punto de equilibrio: cuando dejas de perder",
                    "resumen": "Cuantas unidades necesitas vender para no perder plata.",
                    "duracion_min": 14,
                    "contenido": [
                        {"t": "texto", "h": "El numero magico",
                         "p": "El punto de equilibrio es cuanto tienes que vender para que no te sobre ni te falte. Por debajo, pierdes. Por encima, empiezas a ganar. Saberlo te dice si tu negocio es viable ANTES de arrancar."},
                        {"t": "formula", "h": "Como se calcula",
                         "p": "Punto de equilibrio = Gastos fijos del mes / (Precio - Costo variable por unidad)"},
                        {"t": "ejemplo", "h": "La tienda de arepas",
                         "p": "Gastos fijos: arriendo $600.000 + servicios $200.000 = $800.000. Cada arepa se vende a $3.000 y cuesta $1.000. Margen por arepa: $2.000. Punto de equilibrio = 800.000 / 2.000 = 400 arepas al mes, unas 14 diarias. Si no puedes vender 14 arepas al dia, el negocio no da."},
                        {"t": "tip", "h": "Usalo para decidir",
                         "p": "Si el punto de equilibrio te parece imposible, no montes el negocio: cambia el modelo. Baja gastos fijos, sube el precio o busca mas volumen."},
                    ],
                    "quiz": [
                        {"q": "Gastos fijos $1.000.000, margen por unidad $2.500. ¿Punto de equilibrio?",
                         "op": ["250 unidades", "400 unidades", "2.500 unidades"], "correcta": 1,
                         "explica": "1.000.000 / 2.500 = 400 unidades al mes."},
                    ],
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════
#  CURSO 3 · COMPETENCIAS DIGITALES
# ═══════════════════════════════════════════════════════════════════

DIGITAL = {
    "slug": "digital",
    "titulo": "Competencias Digitales y Ciudadania en Internet",
    "descripcion": (
        "Usar bien la tecnologia: buscar informacion confiable, protegerte en internet, "
        "manejar hojas de calculo y entender que es la inteligencia artificial. "
        "Habilidades que hoy piden en cualquier trabajo."
    ),
    "categoria": "Tecnologia",
    "icono": "💻", "color": "#0EA5E9", "duracion_texto": "6 horas",
    "grado_sugerido": "6-11",
    "modulos": [
        {
            "titulo": "Internet con criterio",
            "descripcion": "Distinguir lo verdadero de lo falso y cuidarte en linea.",
            "nivel": "basico", "icono": "🔍",
            "temas": [
                {
                    "titulo": "Detectar noticias falsas",
                    "resumen": "Cuatro preguntas que desarman casi cualquier mentira en linea.",
                    "duracion_min": 12,
                    "contenido": [
                        {"t": "texto", "h": "Por que caemos",
                         "p": "La informacion falsa se disena para producir una emocion fuerte: rabia o miedo. Cuando algo te indigna mucho, tu cerebro comparte antes de verificar. Esa es exactamente la trampa."},
                        {"t": "tabla", "h": "Las 4 preguntas",
                         "filas": [
                             ["¿Quien lo publica?", "Busca el medio. Si no tiene nombre ni responsable, desconfia"],
                             ["¿Cuando fue?", "Muchas noticias falsas son reales pero viejas, sacadas de contexto"],
                             ["¿Quien mas lo dice?", "Si solo aparece en una pagina, probablemente es falso"],
                             ["¿Que quiere de mi?", "Si te pide compartir urgente o dar datos, es sospechoso"],
                         ]},
                        {"t": "tip", "h": "Truco de la imagen",
                         "p": "Puedes buscar una imagen en Google para ver de donde salio. Muchas fotos 'de ahora' son de hace anos o de otro pais."},
                    ],
                    "quiz": [
                        {"q": "Una senal clara de informacion falsa es:",
                         "op": ["Tiene fotos", "Produce rabia y pide compartir urgente", "Es larga"],
                         "correcta": 1,
                         "explica": "La urgencia emocional es la herramienta principal de la desinformacion."},
                    ],
                },
                {
                    "titulo": "Protege tus datos y tu identidad",
                    "resumen": "Contrasenas, estafas y que nunca debes publicar.",
                    "duracion_min": 13,
                    "contenido": [
                        {"t": "texto", "h": "Tu informacion vale dinero",
                         "p": "Tus datos personales se venden. Por eso te regalan aplicaciones 'gratis': el producto eres tu. No es para asustarte, es para que decidas con conciencia que compartes."},
                        {"t": "tabla", "h": "Reglas basicas",
                         "filas": [
                             ["Contrasenas distintas", "Si te roban una, no pierdes todas tus cuentas"],
                             ["Verificacion en dos pasos", "Activala en correo y redes. Es la mejor proteccion"],
                             ["Nunca compartas codigos", "Ningun banco ni empresa te pide el codigo por WhatsApp"],
                             ["Cuidado con la ubicacion", "Publicar donde estas en tiempo real es riesgoso"],
                         ]},
                        {"t": "ojo", "h": "La estafa mas comun",
                         "p": "Te escriben haciendose pasar por un familiar: 'cambie de numero, necesito un favor urgente'. Siempre verifica llamando al numero viejo antes de enviar nada."},
                    ],
                    "quiz": [
                        {"q": "Si alguien te pide el codigo que te llego por SMS:",
                         "op": ["Se lo das si es del banco", "Nunca lo compartas, es una estafa", "Solo por WhatsApp"],
                         "correcta": 1,
                         "explica": "Ninguna entidad legitima pide ese codigo. Compartirlo es entregar tu cuenta."},
                    ],
                },
            ],
        },
        {
            "titulo": "Herramientas que te dan trabajo",
            "descripcion": "Hojas de calculo e inteligencia artificial.",
            "nivel": "medio", "icono": "📊",
            "temas": [
                {
                    "titulo": "Hojas de calculo desde cero",
                    "resumen": "Las 6 formulas que resuelven el 90% de lo que necesitas.",
                    "duracion_min": 16,
                    "contenido": [
                        {"t": "texto", "h": "La herramienta mas subestimada",
                         "p": "Saber manejar una hoja de calculo aparece en miles de ofertas de empleo. No necesitas ser experto: con seis formulas resuelves la mayoria de tareas reales."},
                        {"t": "tabla", "h": "Las 6 formulas esenciales",
                         "filas": [
                             ["=SUMA(A1:A10)", "Suma un rango de celdas"],
                             ["=PROMEDIO(A1:A10)", "Saca el promedio"],
                             ["=CONTAR(A1:A10)", "Cuenta cuantas celdas tienen numeros"],
                             ["=SI(A1>5;\"Pasa\";\"No pasa\")", "Decide segun una condicion"],
                             ["=BUSCARV(valor;tabla;col;0)", "Busca un dato en otra tabla"],
                             ["=A1*0.19", "Calcula el IVA de una celda"],
                         ]},
                        {"t": "ejemplo", "h": "Tu primera planilla util",
                         "p": "Columna A: producto. Columna B: cantidad. Columna C: precio. En D pones =B2*C2 para el total de cada fila, y abajo =SUMA(D2:D20) para el total general. Ya tienes un registro de ventas funcionando."},
                    ],
                    "quiz": [
                        {"q": "Para sumar de A1 hasta A20 escribes:",
                         "op": ["=SUMA(A1:A20)", "=TOTAL(A1+A20)", "=A1+A20"], "correcta": 0,
                         "explica": "SUMA con dos puntos indica todo el rango entre esas celdas."},
                    ],
                },
                {
                    "titulo": "Inteligencia artificial: usarla bien",
                    "resumen": "Que es realmente, para que sirve y cuando no confiar.",
                    "duracion_min": 15,
                    "contenido": [
                        {"t": "texto", "h": "Que es en realidad",
                         "p": "Una IA de texto no 'sabe' cosas como sabe una persona. Aprendio patrones de millones de textos y predice que sigue. Por eso escribe muy bien y a veces se inventa datos con total seguridad."},
                        {"t": "tip", "h": "Para que si sirve",
                         "p": "Explicarte un tema de otra forma, corregir tu redaccion, darte ideas para empezar, resumir textos largos, ayudarte a estudiar con preguntas."},
                        {"t": "ojo", "h": "Cuando NO confiar",
                         "p": "Datos exactos, fechas, cifras y citas: verificalas siempre. Y si copias tal cual una tarea, no aprendiste nada. Usala como quien pregunta a un companero: te explica, pero el examen lo presentas tu."},
                        {"t": "texto", "h": "Este mismo sistema usa IA",
                         "p": "El sistema de tu colegio usa un modelo que aprende de la asistencia y las notas para detectar quien esta en riesgo de dejar el estudio. No decide por nadie: le avisa a un humano para que actue a tiempo."},
                    ],
                    "quiz": [
                        {"q": "Cuando una IA te da un dato exacto, lo correcto es:",
                         "op": ["Confiar siempre", "Verificarlo en una fuente confiable", "Ignorarlo"],
                         "correcta": 1,
                         "explica": "Las IA pueden generar datos falsos con mucha seguridad. Verifica siempre."},
                    ],
                },
            ],
        },
    ],
}


CURSOS_PREINSTALADOS = [CONTABILIDAD, EMPRENDIMIENTO, DIGITAL]
