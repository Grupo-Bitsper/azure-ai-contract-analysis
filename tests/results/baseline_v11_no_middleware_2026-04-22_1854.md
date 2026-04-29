# Golden set run — baseline_v11_no_middleware

- Fecha: 2026-04-22 18:56:12
- Middleware pre-search: OFF
- Endpoint: `https://rocadesarrollo-resource.services.ai.azure.com/api/projects/rocadesarrollo/openai/v1/responses`
- Agent: `roca-copilot` (versión según version_selector)

## Score

| PASS | PARTIAL | FAIL | SKIP | ERROR | Score gradable |
|---|---|---|---|---|---|
| 6 | 0 | 1 | 1 | 8 | **6/7** |

## Resultados por caso

### R-04 — licencia_construccion — **PASS**

**Prompt:** Dame la licencia de construcción asociado al inmueble RA03 o indícame si no existe en el repositorio

**Esperado:** Devolver RA03_LICENCIA DE CONSTRUCCION.pdf del folder 07. Permiso de construcción con link SharePoint

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `PASS` — matchea: ['licencia', 'construcción', 'RA03_LICENCIA']

**Latencia:** 6201ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
Encontré una licencia de construcción asociada al inmueble RA03, que corresponde a un permiso para la ampliación de nave industrial. Esta licencia fue emitida por la Dirección de Desarrollo Urbano de Ramos Arizpe, Coahuila, con fecha de expedición 16 de agosto de 2022 y tuvo una vigencia de 12 meses, por lo que actualmente está vencida (venció el 16 de agosto de 2023).

Detalles relevantes de la licencia:
- Licencia No. 248, expediente No. 1052/2022.
- Fiduciaria que recibe la licencia: BANCA MIFEL, S.A., con domicilio en Monterrey, Nuevo León.
- Uso de suelo: L - Industria Ligera.
- Superficie total de construcción autorizada para ampliación: 326.265 m².
- Ubicación: Parque Industrial Saltillo - Ramos Arizpe 3ª Etapa.
- Autoridades responsables y señaladas incluyen al arquitecto Haydee Nayeli Castro Gutiérrez como director responsable de obra.
- Monto registrado: 10,779.79 MXN.

Puedes consultar el documento completo en este link de SharePoint:  
[RA03_LICENCIA DE CONSTRUCCIÓN POR ADECUACIONES.pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCA-IAInmuebles/Documentos%20compartidos/07.%20Permisos%20de%20construcci%C3%B3n/RA03_LICENCIA%20DE%20CONSTRUCCI%C3%93N%20POR%20ADECUACIONES.pdf) 【4:5†source】.

Si requieres más información específica sobre esta licencia, por favor indícamelo.
```

---

### R-05 — permisos_vigentes — **PASS**

**Prompt:** Muéstrame los permisos vigentes del inmueble RA03 y devuelve una lista de permisos asociados al inmueble con nombre, autoridad emisora, fecha de emisión y vencimiento

**Esperado:** Lista estructurada de permisos vigentes del folder P03-RA03 con campos nombre/autoridad/emisión/vencimiento

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `PASS` — matchea: ['permiso', 'licencia', 'autoridad', 'vencimiento']

**Latencia:** 5982ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
Para el inmueble RA03, el único documento relacionado con permisos y autorizado por una autoridad que aparece en los documentos indexados es un estudio técnico para el diseño de pavimentos emitido por la Secretaría de Desarrollo Urbano y Obras Públicas.

Detalles del permiso encontrado:
- Nombre del permiso: Diseño de pavimentos (estudio técnico para licencia de construcción)
- Autoridad emisora: Secretaría de Desarrollo Urbano y Obras Públicas
- Fecha de emisión: 20 de septiembre de 2019
- Fecha de vencimiento: No se indica explícitamente fecha de vencimiento en el documento. El estado de vigencia está marcado como "DESCONOCIDO" y no hay fecha para calcular duración. Es necesario verificar manualmente la vigencia.
- Código inmueble: RA03 (NAVE RA03, RA-03, RA03-INV)
- Este documento está ubicado en la siguiente carpeta SharePoint: [Diseño de pavimentos RA-03 REVFINAL.pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/53.%20Dise%C3%B1o%20de%20pavimentos/DISE%C3%91O%20DE%20PAVIMENTOS%20RA-03%20REVFINAL.pdf)

No se encontraron otros permisos vigentes asociados al inmueble RA03 en la documentación disponible.

Si necesitas que busque por otro tipo de permiso o documentos relacionados, dime.  
【4:0†source】【4:1†source】【4:2†source】【4:3†source】【4:4†source】【4:5†source】
```

---

### R-06 — contrato_plazo_cliente — **PASS**

**Prompt:** ¿Cuál es el plazo de vigencia del contrato de arrendamiento del cliente ACTINVER en inmueble RA03?

**Esperado:** Plazo del contrato cuyo arrendatario sea ACTINVER (no Banca Mifel ni Rogers Foam)

**Baseline v11 esperado:** `PARCIAL`

**Verdict automático:** `PASS` — matchea: ['ACTINVER']

**Latencia:** 5872ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
El contrato de arrendamiento del cliente ACTINVER en el inmueble RA03 tiene un plazo inicial de 38 meses a partir de la fecha de inicio del contrato, que es el 20 de mayo de 2022. Además, el contrato contempla 2 periodos de prórroga, cada uno por 3 años.

Específicamente:

- Duración inicial: 38 meses.
- Inicio del contrato: 20 de mayo de 2022.
- Prórrogas: 2 períodos adicionales de 3 años cada uno.

Dado que la fecha exacta de vencimiento no está explícita en el documento, y la vigencia se basa en términos contractuales, se recomienda verificar manualmente para confirmar la vigencia actual. La fecha de procesamiento de la información es 17 de abril de 2026.

Puedes revisar el documento completo aquí: [RA03 Lease Agreement (Signed).pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/30.%20Contrato%20de%20arrendamiento%20y%20anexos/Contrato%20anterior%20Rogers%20Foam%20_%20%20Salida%20en%202024/RA03%20Lease%20Agreement%20(Signed).pdf)【4:0†source】【4:4†source】.
```

---

### R-07 — contrato_version_ultima — **PASS**

**Prompt:** Muéstrame la última versión del contrato de arrendamiento del inmueble RA03

**Esperado:** Versión más reciente con liga SharePoint (2024 > 2022)

**Baseline v11 esperado:** `OK`

**Verdict automático:** `PASS` — matchea: ['2024']

**Latencia:** 8685ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
La última versión del contrato de arrendamiento del inmueble RA03 corresponde al documento denominado "RA03 Lease Agreement (Signed).pdf". 

Este contrato fue emitido el 20 de mayo de 2022 y su vigencia está catalogada como DESCONOCIDA en los metadatos, ya que el documento no contiene fecha explícita de vencimiento. Sin embargo, menciona características como una duración de contrato de 38 meses con posibilidad de 2 prórrogas de 3 años cada una. 

El arrendador es Banca Mifel, Sociedad Anónima, Institución de Banca Múltiple, Grupo Financiero Mifel, y la arrendataria es Rogers Foam México, Sociedad De Responsabilidad Limitada de Capital Variable. La renta mensual pactada es de USD 45,211.35, con un depósito de garantía equivalente a dos meses de renta (USD 90,422.70). La renta se incrementa anualmente con base en el Índice CPI.

El inmueble está identificado en el contrato con los códigos RA03-INV y 0022-247-009, ubicado en Calle Industria Aeroespacial No. 3301, Parque Industrial Saltillo-Ramos, Ramos Arizpe, Coahuila, México.

Puedes consultar el contrato completo en la siguiente liga de SharePoint:
[RA03 Lease Agreement (Signed).pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/30.%20Contrato%20de%20arrendamiento%20y%20anexos/Contrato%20anterior%20Rogers%20Foam%20_%20%20Salida%20en%202024/RA03%20Lease%20Agreement%20(Signed).pdf)

Si deseas que te proporcione detalles más específicos sobre alguna cláusula o aspecto particular del contrato, por favor indícamelo.

【4:0†source】【4:1†source】【4:2†source】【4:3†source】【4:4†source】【4:5†source】
```

---

### R-08 — comparar_versiones — **SKIP**

**Prompt:** Compara la versión actual y anterior del contrato del inmueble RA03

**Esperado:** Diferencias clave entre versiones

**Baseline v11 esperado:** `BLOQUEADO`

**Verdict automático:** `SKIP` — caso bloqueado por data gap (R-08)

**Latencia:** 5426ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
No encontré documentos específicos que contengan una versión anterior del contrato del inmueble RA03 para compararla con la versión actual. En los resultados disponibles está un documento técnico completo sobre diseño y estudio de pavimentos para el proyecto RA-03, pero no se trata de un contrato ni versiones de contrato.

Por favor confirma si te refieres a otro tipo de documento o alguna versión específica, o si deseas que busque documentos contractuales relacionados con otro código o criterio. 

Aquí tienes el documento técnico de diseño de pavimentos RA03 para referencia, aunque no es contrato:
[DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/53.%20Dise%C3%B1o%20de%20pavimentos/DISE%C3%91O%20DE%20PAVIMENTOS%20RA-03%20REVFINAL.pdf)【4:0†source】【4:1†source】【4:2†source】【4:3†source】【4:4†source】【4:5†source】
```

---

### R-09 — resumen_estudio — **ERROR**

**Prompt:** Dame un resumen ejecutivo del estudio de impacto ambiental del inmueble RA03

**Esperado:** Resumen 5-7 bullets del EIA (objetivo, hallazgos, restricciones, fecha) — NO pavimentos

**Baseline v11 esperado:** `PARCIAL`

**Verdict automático:** `ERROR` — HTTP 429: {"error":{"code":"rate_limit_exceeded","message":"Model deployment rate limit exceeded. Too Many Requests. To request more quota, see https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-

**Latencia:** n/ams | **Tool calls:** [] | **Middleware:** False

**Respuesta del agente:**

```
(vacío)
```

---

### R-10 — contrato_resumen — **PASS**

**Prompt:** Dame un resumen ejecutivo de contrato de arrendamiento del inmueble RA03

**Esperado:** Renta mensual, plazo, renovaciones, incrementos, penalizaciones

**Baseline v11 esperado:** `OK`

**Verdict automático:** `PASS` — matchea: ['plazo', 'meses', 'arrendamiento']

**Latencia:** 22296ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
El contrato de arrendamiento del inmueble RA03, cuyo archivo es "RA03 Lease Agreement (Signed).pdf", tiene como arrendador a Banca Mifel, Sociedad Anónima, Institución de Banca Múltiple, Grupo Financiero Mifel. La fecha de emisión del contrato es el 20 de mayo de 2022 y no especifica una fecha de vencimiento explícita, por lo que la vigencia debe verificarse manualmente, considerando que podría tener vigencia relativa (ej. 730 días o 36 meses) desde esa fecha.

Resumen ejecutivo del contrato:

- La propiedad arrendada está al corriente en el pago de contribuciones, incluyendo impuesto predial.
- La arrendataria es responsable de obtener y mantener todas las autorizaciones, licencias y permisos necesarios para operar en el inmueble, entregando copias al arrendador si se solicitan.
- El arrendador realizará una única vez trabajos adicionales en la propiedad, que permanecerán como propiedad del arrendador y no podrán ser modificados sin su consentimiento por escrito. Cualquier cambio solicitado deberá ser pagado por la arrendataria.
- La infraestructura para servicios como electricidad, líneas telefónicas, agua y drenaje está disponible conforme a los requerimientos de la arrendataria, quien cubrirá todos los costos de contratación, conexión y consumo.
- Hay 300 KVAs propiedad del arrendador disponibles para la arrendataria durante el término del contrato, pero la arrendataria debe cubrir todos los gastos derivados y, al término, ofrecer su compra al arrendador al precio de la Comisión Federal de Electricidad.
- La arrendataria paga el impuesto predial y debe reembolsar al arrendador cuotas por actualización catastral, con intereses moratorios en caso de retraso, basados en la tasa Prime de Citibank multiplicada por tres.
- Cualquier retraso en la entrega por medidas gubernamentales prorrogará los plazos respectivos, sin responsabilidad del arrendador, con notificaciones periódicas a la arrendataria.

El documento tiene vigencia desconocida y para consultarlo completo está disponible en SharePoint:
[RA03 Lease Agreement (Signed).pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/30.%20Contrato%20de%20arrendamiento%20y%20anexos/Contrato%20anterior%20Rogers%20Foam%20_%20%20Salida%20en%202024/RA03%20Lease%20Agreement%20(Signed).pdf)【4:0†source】【4:1†source】【4:2†source】【4:3†source】【4:4†source】【4:5†source】
```

---

### R-11 — tabla_permisos — **ERROR**

**Prompt:** Devuelve una lista estándar de permisos con columnas 'Permiso', 'Existe/Falta' y 'Fecha de vencimiento' basada en los documentos cargados en SharePoint del inmueble RA03

**Esperado:** Tabla 3 columnas con Licencia de Construcción 255 (04-oct-2024 Vencida) y Licencia por Adecuaciones 248 (16-ago-2023 Vencida) + links

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `ERROR` — HTTP 429: {"error":{"code":"rate_limit_exceeded","message":"Model deployment rate limit exceeded. Too Many Requests. To request more quota, see https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-

**Latencia:** n/ams | **Tool calls:** [] | **Middleware:** False

**Respuesta del agente:**

```
(vacío)
```

---

### R-12 — permisos_vencimiento_proximo — **PASS**

**Prompt:** Dame los permisos que vencen en los próximos 3 meses en del inmueble RA03, devuelve una lista de permisos con fecha de vencimiento menor o igual a 6 meses a partir de la fecha actual

**Esperado:** 2 licencias con fechas de vencimiento, aclarando que ya están vencidas

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `PASS` — matchea: ['vencimiento', 'fecha']

**Latencia:** 6358ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
No encontré permisos con fecha de vencimiento dentro de los próximos 3 meses ni con vencimiento menor o igual a 6 meses para el inmueble RA03 en la documentación disponible de ROCA. 

En los documentos hallados para RA03, como el estudio técnico de diseño de pavimentos, no se especifica fecha de vencimiento para permisos, o la vigencia está marcada como desconocida, indicando que es necesario verificar manualmente con la autoridad correspondiente para confirmar vigencias.

Si quieres, puedo ayudarte a buscar otro tipo de documentos o verificar con otro criterio. Aquí tienes el link del documento principal consultado:
[DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/53.%20Dise%C3%B1o%20de%20pavimentos/DISE%C3%91O%20DE%20PAVIMENTOS%20RA-03%20REVFINAL.pdf)【4:0†source】【4:1†source】【4:2†source】【4:3†source】【4:4†source】【4:5†source】
```

---

### R-13 — liga_carpeta_cierre — **ERROR**

**Prompt:** Devuelve la liga directa a la carpeta de cierre de proyecto del inmueble RA03 en el sitio de SharePoint

**Esperado:** Link a folder 72. Cartas de entrega con 3 PDFs

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `ERROR` — HTTP 429: {"error":{"code":"rate_limit_exceeded","message":"Model deployment rate limit exceeded. Too Many Requests. To request more quota, see https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-

**Latencia:** n/ams | **Tool calls:** [] | **Middleware:** False

**Respuesta del agente:**

```
(vacío)
```

---

### R-14 — lista_documentos_cliente — **ERROR**

**Prompt:** Devuelve los documentos principales relacionados con el cliente ACTINVER del inmueble RA03 (LOI, contrato, renovaciones, anexos) en una lista con tipo de documento y liga

**Esperado:** Lista de 4 tipos (LOI, contrato, renovaciones, anexos) con link c/u — o 'N/A' explícito por tipo faltante

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `ERROR` — HTTP 429: {"error":{"code":"rate_limit_exceeded","message":"Model deployment rate limit exceeded. Too Many Requests. To request more quota, see https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-

**Latencia:** n/ams | **Tool calls:** [] | **Middleware:** False

**Respuesta del agente:**

```
(vacío)
```

---

### R-15 — planos_asbuilt — **ERROR**

**Prompt:** Devuelve los planos As-Built correspondientes, indicando cuál es la versión más reciente del inmueble RA03

**Esperado:** Planos As-Built con códigos RA03-xxx-xx y fechas

**Baseline v11 esperado:** `OK`

**Verdict automático:** `ERROR` — HTTP 429: {"error":{"code":"rate_limit_exceeded","message":"Model deployment rate limit exceeded. Too Many Requests. To request more quota, see https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-

**Latencia:** n/ams | **Tool calls:** [] | **Middleware:** False

**Respuesta del agente:**

```
(vacío)
```

---

### R-16 — contrato_plazo_consistencia — **ERROR**

**Prompt:** ¿cuál es el plazo de vigencia del contrato de arrendamiento del cliente ACTINVER en RA03?

**Esperado:** 3 años + 2 prórrogas de 3 años forzosas, fechado 05-jul-2024, archivo RA03_Contrato_v1.pdf (ACTINVER específicamente)

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `ERROR` — HTTP 429: {"error":{"code":"rate_limit_exceeded","message":"Model deployment rate limit exceeded. Too Many Requests. To request more quota, see https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-

**Latencia:** n/ams | **Tool calls:** [] | **Middleware:** False

**Respuesta del agente:**

```
(vacío)
```

---

### R-17 — fulltext_search — **ERROR**

**Prompt:** Dame una lista de documentos del inmueble RA03 que mencionen 'servidumbre de paso' en el contenido, no solo en el título, con liga a cada archivo

**Esperado:** RA03-700-09-PASO PARA ACOMETIDA ELECTRICA.pdf (5-ago-2022)

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `ERROR` — HTTP 429: {"error":{"code":"rate_limit_exceeded","message":"Model deployment rate limit exceeded. Too Many Requests. To request more quota, see https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-

**Latencia:** n/ams | **Tool calls:** [] | **Middleware:** False

**Respuesta del agente:**

```
(vacío)
```

---

### R-18 — csf_propietario — **FAIL**

**Prompt:** Dame la constancia de situación fiscal del propietario del inmueble RA03, con razón social, RFC y fecha de emisión visibles en la respuesta

**Esperado:** CSF ROGERS FOAM MEXICO, RFC RFM030526L6A, SAT 16-feb-2022

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `FAIL` — dispara must_not_contain: ['no encontré información sobre la constancia']

**Latencia:** 3680ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
No encontré información sobre la constancia de situación fiscal del propietario del inmueble RA03 en la documentación disponible de ROCA. No se encontró documento específico que contenga razón social, RFC y fecha de emisión visible de esa constancia para ese código de inmueble.

¿Quieres que busque por otro código de inmueble o por otro tipo de documento?
```

---

### R-19 — polizas_seguro — **ERROR**

**Prompt:** Dame las pólizas de seguro vigentes de RA03, y devuelve la lista de pólizas asociadas al inmueble con aseguradora, cobertura principal, suma asegurada, vigencia y liga al documento correspondiente

**Esperado:** Póliza AXA TSA831840000, $13.86M MXN, 3-jun-2022 a 20-sep-2022 (VENCIDA)

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `ERROR` — HTTP 429: {"error":{"code":"rate_limit_exceeded","message":"Model deployment rate limit exceeded. Too Many Requests. To request more quota, see https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-

**Latencia:** n/ams | **Tool calls:** [] | **Middleware:** False

**Respuesta del agente:**

```
(vacío)
```

---
