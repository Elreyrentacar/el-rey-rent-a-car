# EL REY RENT A CAR — Sistema inicial

## Ejecutar localmente
1. Instala Python 3.10 o superior.
2. Abre una terminal dentro de esta carpeta.
3. Ejecuta:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

## Incluye
- Panel administrativo.
- Catálogo de vehículos y tarifas diarias editables.
- Cotizaciones en USD o CRC con tipo de cambio configurable.
- PDF en español, inglés, portugués o francés.
- Historial de cotizaciones en SQLite.
- Lugares de recogida y devolución editables (por defecto SJO).

## Importante sobre las reglas
La regla comercial acordada es: cero horas de cortesía; cualquier devolución posterior a la hora acordada genera un día adicional. El siguiente módulo a completar es el registro de devolución real y el cálculo automático de cargos tardíos. Esta primera versión calcula cotizaciones planificadas y guarda el historial; no gestiona todavía contratos, pagos ni devoluciones reales.

## Publicación
Puedes desplegarlo en Streamlit Community Cloud conectando un repositorio GitHub con estos archivos. Para uso real con varios dispositivos, conviene migrar SQLite a una base de datos alojada y configurar copias de seguridad y acceso privado.
