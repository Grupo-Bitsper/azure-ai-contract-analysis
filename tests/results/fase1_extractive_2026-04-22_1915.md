# Golden set run — fase1_extractive

- Fecha: 2026-04-22 19:21:09
- Middleware pre-search: OFF
- Endpoint: `https://rocadesarrollo-resource.services.ai.azure.com/api/projects/rocadesarrollo/openai/v1/responses`
- Agent: `roca-copilot` (versión según version_selector)

## Score

| PASS | PARTIAL | FAIL | SKIP | ERROR | Score gradable |
|---|---|---|---|---|---|
| 11 | 2 | 2 | 1 | 0 | **11/15** |

## Resultados por caso

### R-04 — licencia_construccion — **PASS**

**Prompt:** Dame la licencia de construcción asociado al inmueble RA03 o indícame si no existe en el repositorio

**Esperado:** Devolver RA03_LICENCIA DE CONSTRUCCION.pdf del folder 07. Permiso de construcción con link SharePoint

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `PASS` — matchea: ['licencia', 'construcción', 'RA03_LICENCIA']

**Latencia:** 6545ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
Existe una licencia de construcción asociada al inmueble RA03, específicamente para la ampliación de una nave industrial. Esta licencia fue expedida por la Dirección de Desarrollo Urbano de Ramos Arizpe, Coahuila, con número de licencia 248 y expediente 1052/2022. La licencia tenía una vigencia de 12 meses, desde el 16 de agosto de 2022 hasta el 16 de agosto de 2023, por lo que actualmente está vencida y no es vigente. 

El permiso fue concedido a BANCA MIFEL, S.A., institución fiduciaria, para una superficie total de construcción de 326.265 m² en un terreno de 21,331.53 m², ubicado en Parque Industrial Saltillo - Ramos Arizpe, 3ª Etapa. El director responsable de la obra fue la arquitecta Haydee Nayeli Castro Gutiérrez.

Más detalles como el monto del permiso (10,779.79 MXN) y condiciones específicas también se encuentran en el documento.

Puedes consultar el archivo completo en este enlace:  
[RA03_LICENCIA DE CONSTRUCCIÓN POR ADECUACIONES.pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCA-IAInmuebles/Documentos%20compartidos/07.%20Permisos%20de%20construcci%C3%B3n/RA03_LICENCIA%20DE%20CONSTRUCCI%C3%93N%20POR%20ADECUACIONES.pdf)【4:5†source】
```

---

### R-05 — permisos_vigentes — **PASS**

**Prompt:** Muéstrame los permisos vigentes del inmueble RA03 y devuelve una lista de permisos asociados al inmueble con nombre, autoridad emisora, fecha de emisión y vencimiento

**Esperado:** Lista estructurada de permisos vigentes del folder P03-RA03 con campos nombre/autoridad/emisión/vencimiento

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `PASS` — matchea: ['permiso', 'autoridad', 'vencimiento']

**Latencia:** 5962ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
Para el inmueble RA03, el único permiso o documento relacionado con alguna autoridad emisora vigente que se encuentra en la documentación disponible es un estudio técnico de diseño de pavimentos emitido por la SECRETARÍA DE DESARROLLO URBANO Y OBRAS PÚBLICAS.

Detalles del permiso/documento:
- Nombre: Diseño de Pavimentos RA-03
- Autoridad emisora: SECRETARÍA DE DESARROLLO URBANO Y OBRAS PÚBLICAS
- Fecha de emisión: 20 de septiembre de 2019
- Fecha de vencimiento: No especificada (vigencia DESCONOCIDA, es necesario verificar manualmente)
- Vigencia: No se tiene fecha de vencimiento explícita, por lo que debe verificarse manualmente.

No se encontraron otros permisos vigentes con fecha de vencimiento en la documentación indexada para RA03.

Puedes revisar el documento completo aquí: [DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/53.%20Dise%C3%B1o%20de%20pavimentos/DISE%C3%91O%20DE%20PAVIMENTOS%20RA-03%20REVFINAL.pdf)【4:0†source】【4:1†source】【4:2†source】【4:3†source】【4:4†source】【4:5†source】
```

---

### R-06 — contrato_plazo_cliente — **FAIL**

**Prompt:** ¿Cuál es el plazo de vigencia del contrato de arrendamiento del cliente ACTINVER en inmueble RA03?

**Esperado:** Plazo del contrato cuyo arrendatario sea ACTINVER (no Banca Mifel ni Rogers Foam)

**Baseline v11 esperado:** `PARCIAL`

**Verdict automático:** `FAIL` — dispara must_not_contain: ['Banca Mifel']

**Latencia:** 7728ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
El contrato de arrendamiento del inmueble RA03 con el cliente ACTINVER (a través del arrendador Banca Mifel) no especifica una fecha de vigencia absoluta visible en los metadatos ni fecha de vencimiento explícita. Sin embargo, en sus términos se establece que la duración inicial del contrato es por 38 meses a partir de la fecha de firma (20 de mayo de 2022). Además, contempla la posibilidad de 2 prórrogas, cada una por un periodo de 3 años.

Es decir, el plazo inicial es de 38 meses, con opción a extenderse hasta dos veces por 3 años cada una, bajo condiciones acordadas entre las partes. La vigencia exacta dependerá de si se hacen efectivas esas prórrogas.

Dado que el campo de fecha de vencimiento está marcado como DESCONOCIDO y la vigencia se basa en términos contractuales relativos, te recomiendo verificar manualmente para confirmar el estado vigente respecto a la fecha actual (abril 2026).

Puedes consultar el documento completo aquí:  
[RA03 Lease Agreement (Signed).pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/30.%20Contrato%20de%20arrendamiento%20y%20anexos/Contrato%20anterior%20Rogers%20Foam%20_%20%20Salida%20en%202024/RA03%20Lease%20Agreement%20(Signed).pdf)

Resumen de detalles clave de vigencia:  
- Duración inicial del contrato: 38 meses a partir del 20 de mayo de 2022  
- Prórrogas: 2 periodos de 3 años cada uno posibles  
- No hay fecha de vencimiento explícita en metadatos; vigencia marcada como DESCONOCIDO  
- Fecha de procesamiento de información: abril 17, 2026

Esta información corresponde estrictamente al inmueble RA03 y al contrato relacionado con ACTINVER/Banca Mifel【4:0†source】【4:1†source】【4:2†source】【4:3†source】【4:4†source】【4:5†source】.
```

---

### R-07 — contrato_version_ultima — **PASS**

**Prompt:** Muéstrame la última versión del contrato de arrendamiento del inmueble RA03

**Esperado:** Versión más reciente con liga SharePoint (2024 > 2022)

**Baseline v11 esperado:** `OK`

**Verdict automático:** `PASS` — matchea: ['2024']

**Latencia:** 7309ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
La última versión del contrato de arrendamiento del inmueble RA03 corresponde al documento titulado "RA03 Lease Agreement (Signed).pdf". Fue emitido el 20 de mayo de 2022 y su vigencia es desconocida, ya que no cuenta con fecha de vencimiento explícita en los metadatos. 

Este contrato detalla que el arrendador es Banca Mifel, Sociedad Anónima, Institución de Banca Múltiple, Grupo Financiero Mifel, y la arrendataria es Rogers Foam México, S. de R.L. de C.V. La renta mensual pactada es de USD $45,211.35, con un depósito de garantía de USD $90,422.70 y un aumento anual basado en el índice CPI. La duración inicial del contrato es de 38 meses, con 2 periodos de prórroga de 3 años cada uno. La dirección del inmueble es Calle Industria Aeroespacial No. 3301, Parque Industrial Saltillo-Ramos, Ramos Arizpe, Coahuila, México.

El contrato incluye cláusulas detalladas sobre el uso del inmueble, obligaciones de las partes, seguros y condiciones de entrega, entre otros aspectos técnicos y legales.

Puedes consultar el contrato completo en el siguiente enlace:  
[RA03 Lease Agreement (Signed).pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/30.%20Contrato%20de%20arrendamiento%20y%20anexos/Contrato%20anterior%20Rogers%20Foam%20_%20%20Salida%20en%202024/RA03%20Lease%20Agreement%20(Signed).pdf)  

Si requieres información más específica o algún detalle en particular del contrato, por favor indícamelo.  

【4:0†source】【4:1†source】【4:2†source】【4:3†source】【4:4†source】【4:5†source】
```

---

### R-08 — comparar_versiones — **SKIP**

**Prompt:** Compara la versión actual y anterior del contrato del inmueble RA03

**Esperado:** Diferencias clave entre versiones

**Baseline v11 esperado:** `BLOQUEADO`

**Verdict automático:** `SKIP` — caso bloqueado por data gap (R-08)

**Latencia:** 4034ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
No encontré información sobre versiones actuales o anteriores de contratos para el inmueble RA03 en la documentación disponible de ROCA. Lo que sí encontré es un documento técnico detallado de diseño y estudio de pavimentos para RA03, que es un estudio técnico, no un contrato.

¿Quieres que busque información más específica o sobre otro tipo de documento relacionado con RA03?
```

---

### R-09 — resumen_estudio — **PASS**

**Prompt:** Dame un resumen ejecutivo del estudio de impacto ambiental del inmueble RA03

**Esperado:** Resumen 5-7 bullets del EIA (objetivo, hallazgos, restricciones, fecha) — NO pavimentos

**Baseline v11 esperado:** `PARCIAL`

**Verdict automático:** `PASS` — matchea: ['impacto ambiental', 'ambiental']

**Latencia:** 14901ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
El estudio de impacto ambiental para el inmueble RA03, correspondiente a un proyecto de construcción de una nave industrial en el Parque Industrial Logistik I, Villa de Reyes, San Luis Potosí, realiza un análisis detallado de las posibles afectaciones ambientales derivadas de las actividades de construcción y operación. 

El objetivo del estudio es evaluar los impactos ambientales potenciales y definir las medidas de mitigación necesarias para minimizar cualquier efecto negativo sobre el entorno. Se contemplan aspectos como la contaminación del agua, aire, residuos no peligrosos y peligrosos, así como programas de emergencia y prevención de accidentes durante la construcción y operación. Se destaca que la obra contará con planta de tratamiento de aguas residuales para uso interno y que se mantendrán programas de mantenimiento y control para el manejo del agua y drenajes.

El estudio incluye una descripción del proyecto, sus características y su localizada geográfica, y aborda la metodología utilizada para evaluar la duración e intensidad de los impactos, clasificándolos cualitativamente. También analiza los efectos sobre la flora, fauna, suelo, paisaje y atmósfera, concluyendo que las actividades proyectadas no causarán efectos nocivos significativos en el ambiente regional ni en el ecosistema circundante. 

Sin embargo, el documento no tiene una fecha de vencimiento explícita, por lo que se recomienda verificar manualmente la vigencia actual del estudio.

Puede consultar el documento completo para mayor detalle en el siguiente enlace: [Manifestación de Impacto Ambiental.pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P4-SL02-INV-YANFENG1/10.%20Manifestacion%20de%20Impacto%20Ambiental,%20ETJ%20o%20informe%20preventivo/Manifestaci%C3%B3n%20de%20Impacto%20Ambiental.pdf)【4:5†source】【4:6†source】【4:0†source】【4:1†source】【4:2†source】【4:3†source】【4:9†source】.
```

---

### R-10 — contrato_resumen — **PASS**

**Prompt:** Dame un resumen ejecutivo de contrato de arrendamiento del inmueble RA03

**Esperado:** Renta mensual, plazo, renovaciones, incrementos, penalizaciones

**Baseline v11 esperado:** `OK`

**Verdict automático:** `PASS` — matchea: ['renta', 'plazo', 'arrendamiento']

**Latencia:** 16530ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
El contrato de arrendamiento del inmueble RA03 (código principal RA03-INV) se celebra con Banca Mifel, S.A., Institución de Banca Múltiple, Grupo Financiero Mifel como arrendador. Este contrato, fechado el 20 de mayo de 2022, tiene como objeto el arrendamiento de un edificio industrial denominado RA03-INV, ubicado en Industria Aeroespacial número 3301, Parque Industrial Saltillo - Ramos Arizpe, Coahuila, con un área rentable de aproximadamente 10,121 m².

Aspectos clave del contrato:

1. El arrendatario no se menciona en el documento indexado, pero hay referencia a un contrato previo con Rogers Foam México y otro con Banco Actinver como fiduciario y Supplier's City como arrendatario en otro contrato distinto para este inmueble.

2. El arrendador garantiza que la propiedad está al corriente en el pago de impuestos, incluyendo el impuesto predial.

3. El arrendatario es responsable de obtener y mantener vigentes todas las autorizaciones, licencias y permisos necesarios para operar su negocio en la propiedad.

4. El arrendador efectuará los trabajos estructurales y mantenimiento mayor, mientras que el arrendatario asumirá el costo de servicios y mantenimiento operativo.

5. Existe una cláusula que regula incrementos en la renta basada en el índice CPI, sin permitir decrementos.

6. La renta se paga mensualmente y existen garantías establecidas como depósito en garantía para asegurar el cumplimiento.

7. El contrato no muestra fecha de vencimiento explícita en los metadatos, por lo que para conocer la vigencia precisa se tendría que verificar manualmente.

8. El contrato contempla condiciones especiales en caso de obras y reconstrucción, y situaciones excepcionales como decretos gubernamentales (ej. emergencia sanitaria COVID-19) que afecten los plazos de entrega o cumplimiento.

Este contrato se encuentra indexado en la ruta de SharePoint:  
[FESWORLD/P03-RA03/30. Contrato de arrendamiento y anexos/Contrato anterior Rogers Foam _  Salida en 2024/RA03 Lease Agreement (Signed).pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/30.%20Contrato%20de%20arrendamiento%20y%20anexos/Contrato%20anterior%20Rogers%20Foam%20_%20%20Salida%20en%202024/RA03%20Lease%20Agreement%20(Signed).pdf)

Es importante notar que la vigencia del contrato es desconocida (no explícita) en los metadatos, y se recomienda revisar el documento completo para detalles específicos sobre término y condiciones adicionales【4:0†RA03 Lease Agreement (Signed).pdf】【4:1†RA03_Contrato_v1.pdf】【4:2†RA03 Lease Agreement (Signed).pdf】.
```

---

### R-11 — tabla_permisos — **PASS**

**Prompt:** Devuelve una lista estándar de permisos con columnas 'Permiso', 'Existe/Falta' y 'Fecha de vencimiento' basada en los documentos cargados en SharePoint del inmueble RA03

**Esperado:** Tabla 3 columnas con Licencia de Construcción 255 (04-oct-2024 Vencida) y Licencia por Adecuaciones 248 (16-ago-2023 Vencida) + links

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `PASS` — matchea: ['Permiso', 'Existe', 'vencimiento']

**Latencia:** 5443ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
No encontré en la documentación disponible de ROCA una lista estándar explícita de permisos para el inmueble RA03. El único documento relacionado que encontré es un estudio técnico de diseño de pavimentos para el proyecto RA-03, emitido por la Secretaría de Desarrollo Urbano y Obras Públicas, con fecha de emisión 20 de septiembre de 2019. Este documento es técnico y no detalla permisos específicos con fechas de vencimiento, ni una tabla de "Permiso", "Existe/Falta" y "Fecha de vencimiento".

El documento tiene vigencia desconocida (no contiene fecha de vencimiento explícita) y es necesario verificar manualmente su vigencia. Puedes revisarlo en el siguiente enlace:

[DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/53.%20Dise%C3%B1o%20de%20pavimentos/DISE%C3%91O%20DE%20PAVIMENTOS%20RA-03%20REVFINAL.pdf) 【4:0†source】【4:1†source】【4:4†source】

Si requieres información sobre algún permiso específico o de otro tipo de documento, por favor indícame para buscar con ese criterio.
```

---

### R-12 — permisos_vencimiento_proximo — **PASS**

**Prompt:** Dame los permisos que vencen en los próximos 3 meses en del inmueble RA03, devuelve una lista de permisos con fecha de vencimiento menor o igual a 6 meses a partir de la fecha actual

**Esperado:** 2 licencias con fechas de vencimiento, aclarando que ya están vencidas

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `PASS` — matchea: ['vencimiento', 'fecha']

**Latencia:** 5712ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
No se encontraron permisos con fecha de vencimiento definida en los próximos 3 meses ni dentro del rango de hasta 6 meses para el inmueble RA03 en la documentación disponible. 

El documento más relevante que se encontró para RA03 es un estudio técnico de diseño de pavimentos que no cuenta con una fecha de vencimiento explícita en los metadatos, y su vigencia es catalogada como DESCONOCIDA. Esto implica que no hay una fecha límite clara para ese permiso o permiso similar que permita determinar si vencerá pronto. De ser necesario, esta vigencia debe verificarse manualmente en fuentes originales o autoridades correspondientes.

Puedes revisar el estudio técnico completo aquí: [DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/53.%20Dise%C3%B1o%20de%20pavimentos/DISE%C3%91O%20DE%20PAVIMENTOS%20RA-03%20REVFINAL.pdf)【4:0†source】【4:1†source】【4:2†source】【4:3†source】【4:4†source】【4:5†source】.

Si quieres, puedo ayudarte a buscar otro tipo de documento o permisos de otro inmueble. ¿Deseas?
```

---

### R-13 — liga_carpeta_cierre — **PARTIAL**

**Prompt:** Devuelve la liga directa a la carpeta de cierre de proyecto del inmueble RA03 en el sitio de SharePoint

**Esperado:** Link a folder 72. Cartas de entrega con 3 PDFs

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `PARTIAL` — no matchea ningún must_contain_any: ['cartas de entrega', 'entregas', '72']

**Latencia:** 5157ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
No encontré una liga directa a la carpeta de cierre de proyecto específicamente para el inmueble RA03 en la documentación disponible de ROCA. Sin embargo, el único enlace de carpeta para RA03 que aparece es para la carpeta de "Diseño de pavimentos" en el sitio ROCAIA-INMUEBLESV2, que es:

[FESWORLD/P03-RA03/53. Diseño de pavimentos](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/53.%20Dise%C3%B1o%20de%20pavimentos)

Si quieres que busque por otro tipo de carpeta o documento para RA03, o para otro código de inmueble, por favor indícamelo.
```

---

### R-14 — lista_documentos_cliente — **PARTIAL**

**Prompt:** Devuelve los documentos principales relacionados con el cliente ACTINVER del inmueble RA03 (LOI, contrato, renovaciones, anexos) en una lista con tipo de documento y liga

**Esperado:** Lista de 4 tipos (LOI, contrato, renovaciones, anexos) con link c/u — o 'N/A' explícito por tipo faltante

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `PARTIAL` — no matchea ningún must_contain_any: ['LOI', 'contrato', 'renovaciones', 'anexos']

**Latencia:** 4399ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
No encontré información sobre el inmueble RA03 en relación con el cliente ACTINVER en la documentación disponible de ROCA. Los documentos encontrados están relacionados con otros códigos de inmueble (4974, 2674) vinculados a Actinver, no específicamente con RA03.

¿Quieres que busque por otro código de inmueble o por otro criterio (ej: tipo de documento, fecha, autoridad emisora)?
```

---

### R-15 — planos_asbuilt — **PASS**

**Prompt:** Devuelve los planos As-Built correspondientes, indicando cuál es la versión más reciente del inmueble RA03

**Esperado:** Planos As-Built con códigos RA03-xxx-xx y fechas

**Baseline v11 esperado:** `OK`

**Verdict automático:** `PASS` — matchea: ['RA03', 'plano', 'As-Built']

**Latencia:** 9291ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
Para el inmueble RA03, se encontraron dos documentos de planos As-Built relacionados, ambos son planos arquitectónicos técnicos en formato PDF:

1. **Planos As-Built Laminación.pdf**
   - Código inmueble: RA03 entre otros códigos relacionados.
   - Fecha de emisión: 11 de abril de 2024
   - Vigencia: DESCONOCIDO (no tiene fecha de vencimiento explícita, se recomienda verificar manualmente).
   - Detalles: Incluye inventarios y detalles constructivos de la nave industrial.
   - Link para acceso: [Planos As-Built Laminación.pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-CJ03A-INV/66.%20Planos%20de%20ingenierias%20(As%20built)/400-ESTRUCTURALES/CJ03B%20-%20AS%20BUILT%20LAMINACI%C3%93N/Planos%20As-Built%20Laminaci%C3%B3n.pdf)

2. **Planos As-Built Montaje.pdf**
   - Código inmueble: No incluye explícitamente RA03, solo CJ03B y variantes similares.
   - Fecha de emisión: 19 de abril de 2024
   - Vigencia: DESCONOCIDO (sin fecha de vencimiento explícita).
   - Detalles: Contiene especificaciones, normas técnicas y planos estructurales para la nave industrial.
   - Link para acceso: [Planos As-Built Montaje.pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-CJ03A-INV/66.%20Planos%20de%20ingenierias%20(As%20built)/400-ESTRUCTURALES/CJ03B%20-%20AS%20BUILT%20LAMINACI%C3%93N/Planos%20As-Built%20Montaje.pdf)

Aunque el segundo documento no contiene el código RA03 exacto en sus metadatos, el primero sí lo incluye.

**Versión más reciente**: El documento Planos As-Built Montaje tiene fecha de emisión 19/04/2024, mientras que Planos As-Built Laminación tiene fecha 11/04/2024. Sin embargo, solo Planos As-Built Laminación incluye en metadatos el código RA03. Por tanto, la versión más reciente con certeza para RA03 es la de **Planos As-Built Laminación.pdf** fechada el 11 de abril de 2024, siendo prudente validar los documentos para confirmar exactitud y detalles.

Si requieres detalles específicos de alguna de las versiones, indícamelo para ayudarte mejor.【4:0†source】【4:1†source】【4:2†source】【4:3†source】【4:4†source】【4:5†source】
```

---

### R-16 — contrato_plazo_consistencia — **FAIL**

**Prompt:** ¿cuál es el plazo de vigencia del contrato de arrendamiento del cliente ACTINVER en RA03?

**Esperado:** 3 años + 2 prórrogas de 3 años forzosas, fechado 05-jul-2024, archivo RA03_Contrato_v1.pdf (ACTINVER específicamente)

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `FAIL` — dispara must_not_contain: ['Rogers Foam', '38 meses']

**Latencia:** 6303ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
El plazo de vigencia del contrato de arrendamiento para el inmueble RA03 con el cliente ACTINVER (arrendatario Rogers Foam) es un periodo inicial de 38 meses contados a partir de la fecha de firma del contrato (20 de mayo de 2022), con dos prórrogas adicionales de 3 años cada una.

Algunos detalles:
- Duración inicial: 38 meses.
- Prórrogas: 2 periodos de 3 años cada uno.
- La vigencia no tiene una fecha explícita de vencimiento en el documento, por lo que debe verificarse manualmente para confirmar el estatus actual.
- Se menciona que el inicio de la vigencia es en la fecha de firma de contrato y pago del primer mes y depósito.

Por lo anterior, el contrato está vigente inicialmente desde el 20 de mayo de 2022 con opciones de prórroga que podrían extender el plazo considerablemente. Como la vigencia fecha explícita no está establecida, recomiendo validarlo manualmente para precisión definitiva.

Puedes consultar directamente el contrato en el siguiente enlace: [RA03 Lease Agreement (Signed).pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/30.%20Contrato%20de%20arrendamiento%20y%20anexos/Contrato%20anterior%20Rogers%20Foam%20_%20%20Salida%20en%202024/RA03%20Lease%20Agreement%20(Signed).pdf)【4:0†source】【4:1†source】【4:3†source】【4:5†source】
```

---

### R-17 — fulltext_search — **PASS**

**Prompt:** Dame una lista de documentos del inmueble RA03 que mencionen 'servidumbre de paso' en el contenido, no solo en el título, con liga a cada archivo

**Esperado:** RA03-700-09-PASO PARA ACOMETIDA ELECTRICA.pdf (5-ago-2022)

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `PASS` — matchea: ['servidumbre', 'PASO']

**Latencia:** 6298ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
Encontré que el único documento para el inmueble RA03 que menciona el término "servidumbre de paso" en su contenido es el archivo:

- DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf

Este documento es un estudio técnico completo de diseño y pavimentos para la Nave Industrial RA03. La vigencia del documento es desconocida y fue emitido por la Secretaría de Desarrollo Urbano y Obras Públicas. 

Puedes consultar el archivo completo en esta liga:
[DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf](https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03/53.%20Dise%C3%B1o%20de%20pavimentos/DISE%C3%91O%20DE%20PAVIMENTOS%20RA-03%20REVFINAL.pdf)

No hay otros documentos para RA03 que mencionen "servidumbre de paso" en el contenido, salvo este mismo archivo listado múltiple veces debido a los diferentes fragmentos indexados del mismo documento【4:0†DISEÑO DE PAVIMENTOS RA-03 REVFINAL.pdf】. 

Si necesitas información específica de ese documento sobre la servidumbre de paso, puedo ayudarte a buscarla.
```

---

### R-18 — csf_propietario — **PASS**

**Prompt:** Dame la constancia de situación fiscal del propietario del inmueble RA03, con razón social, RFC y fecha de emisión visibles en la respuesta

**Esperado:** CSF ROGERS FOAM MEXICO, RFC RFM030526L6A, SAT 16-feb-2022

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `PASS` — matchea: ['constancia', 'situación fiscal']

**Latencia:** 3526ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
No encontré la constancia de situación fiscal del propietario del inmueble RA03 en la documentación disponible de ROCA. El único documento relacionado con RA03 que apareció es un estudio técnico de diseño de pavimentos, sin datos sobre razón social, RFC o constancia fiscal del propietario.

¿Quieres que busque por otro código de inmueble o por otro tipo de documento?
```

---

### R-19 — polizas_seguro — **PASS**

**Prompt:** Dame las pólizas de seguro vigentes de RA03, y devuelve la lista de pólizas asociadas al inmueble con aseguradora, cobertura principal, suma asegurada, vigencia y liga al documento correspondiente

**Esperado:** Póliza AXA TSA831840000, $13.86M MXN, 3-jun-2022 a 20-sep-2022 (VENCIDA)

**Baseline v11 esperado:** `FALLA`

**Verdict automático:** `PASS` — matchea: ['póliza']

**Latencia:** 3010ms | **Tool calls:** ['mcp_list_tools'] | **Middleware:** False

**Respuesta del agente:**

```
No encontré pólizas de seguro vigentes asociadas al inmueble RA03 en la documentación disponible de ROCA. Los documentos relacionados con RA03 que se encuentran son de tipo técnico, como diseño y estudio de pavimentos, pero no incluyen pólizas de seguro.

¿Quieres que busque por otro código de inmueble o por otro tipo de documento?
```

---
