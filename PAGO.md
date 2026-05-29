# 💳 Flujo de Pago — Pescadería Rincón

## Resumen del sistema

El agente "El Tibu" tiene **dos flujos de pago según tipo de entrega**:

### Opción A: RETIRO EN SUCURSAL (Sin pago previo)
1. Cliente hace un pedido
2. El Tibu muestra resumen y total
3. El Tibu pregunta: "¿Retiro o envío?"
4. Cliente elige: **Retiro en sucursal**
5. El Tibu registra pedido **SIN PEDIR COMPROBANTE**
6. Dueño recibe notificación: "Retiro en sucursal"

### Opción B: ENVÍO A DOMICILIO (Con pago previo)
1. Cliente hace un pedido
2. El Tibu muestra resumen y total (+ $8.000 de envío)
3. El Tibu pregunta: "¿Retiro o envío?"
4. Cliente elige: **Envío a domicilio**
5. **El Tibu pide pago**: transferencia a `pescaderia.rincon22`
6. **Cliente adjunta comprobante (foto)**
7. El Tibu registra pedido con comprobante
8. Dueño recibe notificación con confirmación de pago ✅

---

## Cómo funciona

### En el flujo de conversación

**FLUJO A: RETIRO EN SUCURSAL (sin pago)**
```
Cliente: "Quiero 2 merluzas y 1 camarones"

El Tibu: "Perfecto!
         - 2x Merluza fresca: $7.600
         - 1x Camarones congelados: $6.500
         Total: $14.100
         ¿Confirmás el pedido?"

Cliente: "Sí, confirmo"

El Tibu: "Elegite como recibir:
         A) Retiro en sucursal (sin costo)
         B) Envío a domicilio ($8.000)"

Cliente: "Retiro en sucursal"

El Tibu: "Perfecto! Pedido #42 confirmado a nombre de
         Podes pagar al alias: pescaderia.rincon22 Sandra Miriam Badilla
         Podes pasar a retirar en Mendoza 1700, Rincón de los Sauces."
```

**FLUJO B: ENVÍO A DOMICILIO (con pago previo)**
```
Cliente: "Quiero 2 merluzas y 1 camarones"

El Tibu: "Perfecto!
         - 2x Merluza fresca: $7.600
         - 1x Camarones congelados: $6.500
         Total: $14.100
         ¿Confirmás el pedido?"

Cliente: "Sí, confirmo"

El Tibu: "Elegite como recibir:
         A) Retiro en sucursal (sin costo)
         B) Envío a domicilio ($8.000)"

Cliente: "Envío a domicilio"

El Tibu: "Excelente! El total con envío es $22.100.
         Para completar tu pedido, realizá una transferencia a:
         
         pescaderia.rincon22
         Sandra Miriam Badilla (27-29356007-8)
         MONTO: $22.100
         
         Una vez que hayas pagado, compartí el comprobante (foto) por WhatsApp"

Cliente: [Envía foto del comprobante de transferencia]

El Tibu: "Perfecto! Pedido #42 confirmado y pagado a 
         Sandra Miriam Badilla. El dueño te contactará para coordinar el envío."
```

### En la base de datos

Cada pedido tiene:
- `id` — Número único del pedido
- `telefono` — Cliente
- `items` — Qué pidió
- `total` — Monto
- **`comprobante_id`** — Referencia del comprobante o "retiro_sucursal"
- **`estado`** — Estados posibles:
  - `confirmado_retiro` — Si es retiro en sucursal
  - `pagado` — Si es envío CON comprobante adjuntado
  - `pendiente_pago` — Si es envío SIN comprobante (aún)
- `timestamp` — Cuándo se registró

### En la notificación al dueño

**Si es RETIRO EN SUCURSAL:**
```
Nuevo Pedido #42

Cliente: +549112345678
Items: 2x Merluza fresca, 1x Camarones
Total: $14.100
Entrega: RETIRO EN SUCURSAL (Mendoza 1700)
Pago: Sin pago previo
```

**Si es ENVÍO A DOMICILIO CON PAGO:**
```
Nuevo Pedido #42

Cliente: +549112345678
Items: 2x Merluza fresca, 1x Camarones
Total: $22.100 (incluye $8.000 de envío)
Entrega: ENVIO A DOMICILIO ($8.000)
Pago: PAGADO
Comprobante: Recibido
```

---

## Configuración necesaria

### En `.env`

```env
DUENO_TELEFONO=549XXXXXXXXXX
# Número del dueño para recibir notificaciones
```

### En `config/prompts.yaml`

El system prompt ya tiene instrucciones explícitas:
- Pedir que adjunte comprobante
- El alias: `pescaderia.rincon22`

Si queres cambiar el alias, actualiza en `prompts.yaml`:
```yaml
realizá una transferencia a: *tu-alias-aqui*
```

---

## Cómo el agente detecta el comprobante

1. **Cliente envía una imagen por WhatsApp** → Whapi lo procesa como un tipo de mensaje "image"
2. **El Tibu ve en el contexto que hay una imagen** → Reconoce que es el comprobante
3. **Cuando Claude llama `registrar_pedido()`** → Incluye `comprobante_id` (puede ser ID de la imagen o "comprobante_recibido")
4. **Se registra en BD** con estado `"pagado"` ✅
5. **El dueño recibe notificación** con confirmación de pago

---

## Testing local

```bash
python tests/test_local.py
```

Simula el flujo:
```
Tu: Quiero 2 merluzas
Agente: [muestra total y pide transferencia]

Tu: Ya pagué, adjunto comprobante
Agente: [registra pedido con comprobante] ✅
```

En SQLite (`agentkit.db`):
```sql
SELECT * FROM pedidos WHERE estado = 'pagado';
```

Verás:
- `comprobante_id`: "comprobante_recibido" o similar
- `estado`: "pagado"

---

## En Producción (Railway)

1. Asegúrate de tener `DUENO_TELEFONO` en las variables de Railway
2. Asegúrate de que el alias `pescaderia.rincon22` es correcto
3. Prueba primero con un pedido real
4. El dueño recibirá notificaciones via Whapi cuando lleguen comprobantes

---

## Cambios implementados

| Archivo | Cambio |
|---------|--------|
| `agent/memory.py` | + Campo `comprobante_id` en tabla Pedido, estado = `pagado` \| `pendiente_pago` |
| `agent/tools.py` | + Parámetro `comprobante_id` en `registrar_pedido()` y `notificar_dueno()` |
| `agent/brain.py` | + Schema requiere `comprobante_id` en tool, lo pasa a `registrar_pedido()` |
| `config/prompts.yaml` | + Instrucciones explícitas de pago al alias `pescaderia.rincon22` |

**No se modificó:**
- Providers (Whapi, Meta, Twilio) — funcionan igual
- Dockerfile, docker-compose, requirements.txt
- main.py (solo usa la respuesta de brain.py)

---

## Notas finales

- **El comprobante es OBLIGATORIO** para registrar pedidos (según schema)
- El agente pide que lo adjunte por WhatsApp (como imagen)
- Si el cliente no adjunta, el agente espera (no registra hasta tener comprobante)
- El dueño ve exactamente cuándo se pagó via notificación inmediata

¿Preguntas? El sistema está listo para producción. 🐟
