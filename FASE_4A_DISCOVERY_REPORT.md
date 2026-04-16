# Fase 4A — Reporte de Discovery (schema data-driven)

_Este reporte es evidencia forense del estado del dataset en el momento del discovery. No editar a mano — si hay errores, documenta objeciones en `FASE_4A_SCHEMA_PROPUESTO.md` o en un archivo separado._

## 1. Metadatos de la corrida

- **PDFs físicos en muestra (con duplicados)**: 45
- **PDFs únicos por content_hash**: 38
- **Grupos de duplicados detectados**: 5 (ver §14)
- **Discovery outputs procesados**: 38
- **Outputs válidos (JSON parseado)**: 38
- **Parse errors**: 0
- **Outputs vacíos**: 0
- **Tokens prompt**: 353,880
- **Tokens completion**: 105,067
  - de los cuales reasoning: 55,552 (52.9% del completion)

## 2. Resumen ejecutivo (5 bullets)

- Dataset real de ROCA consiste en **múltiples tipos heterogéneos** (contratos, licencias, CSFs, planos, estudios ambientales, poderes legales) — NO es un dataset mono-tipo.
- Los códigos de inmueble siguen patrones distintos entre sites — `RAxx`, `REx`, `GUAxx`, `SLxx`, `FESxxxx` — lo que implica que `inmueble_codigo` en Capa 2 debe ser un `Collection(Edm.String)` y no un `string` simple.
- Los documentos contienen datos fiscales (**RFCs**) y personales (**CURPs, domicilios**) — cualquier exposición de metadata al usuario final debe respetar trimming por grupo SharePoint.
- Las **fechas** aparecen en 2-3 formatos distintos dentro del mismo dataset — normalizar en ingesta a `DateTimeOffset`.
- Los **planos arquitectónicos** son PDFs image-heavy con texto muy limitado — el embedding-based search sobre ellos será débil; son candidato a `doc_type=plano` con búsqueda basada en nombre de archivo y folder_path más que en contenido.

## 3. Distribución de tipos de documento (según gpt-5-mini)

| tipo_documento | cantidad |
|---|---|
| `plano_arquitectonico` | 13 |
| `constancia_situacion_fiscal` | 8 |
| `licencia_construccion` | 3 |
| `estudio_ambiental` | 1 |
| `acta_asamblea` | 1 |
| `escritura_publica` | 1 |
| `contrato_arrendamiento` | 1 |
| `escritura_publica_acta_asamblea` | 1 |
| `constancia_curp` | 1 |
| `recibo_servicio` | 1 |
| `contrato_compraventa` | 1 |
| `estados_financieros_auditados` | 1 |
| `constancia_uso_suelo` | 1 |
| `factura_electronica` | 1 |
| `estudio_geotecnico` | 1 |
| `contrato_desarrollo_inmobiliario` | 1 |
| `garantia_corporativa` | 1 |

### Cruce tipo × carpeta canónica

| Carpeta canónica (origen SharePoint) | Tipos detectados por el modelo |
|---|---|
| `07._Permisos_de_construcci_n` | `licencia_construccion` (3) |
| `11._Estudio_fase_I_-_Ambiental` | `estudio_ambiental` (1) |
| `30._Contrato_de_arrendamiento_y_anexos` | `acta_asamblea` (1), `escritura_publica` (1), `contrato_arrendamiento` (1) |
| `33._Constancia_situacion_fiscal` | `constancia_situacion_fiscal` (4) |
| `65._Planos_arquitectonicos_As_built` | `plano_arquitectonico` (5) |
| `Biblioteca_de_suspensiones_de_conservaci_n` | `constancia_situacion_fiscal` (3), `escritura_publica_acta_asamblea` (1), `constancia_curp` (1), `recibo_servicio` (1), `contrato_compraventa` (1), `estados_financieros_auditados` (1) |
| `FESWORLD` | `plano_arquitectonico` (8), `factura_electronica` (1), `estudio_geotecnico` (1), `contrato_desarrollo_inmobiliario` (1), `constancia_situacion_fiscal` (1), `garantia_corporativa` (1) |
| `Principal` | `constancia_uso_suelo` (1) |

## 4. Densidad de campos (aparición en la muestra)

Porcentaje de docs con cada campo en _no-null_ (n = docs con output válido).

| Campo | % docs con valor | rationale para ubicación en schema |
|---|---|---|
| `tipo_documento` | 100% | Capa 2 (universal, filtrable) |
| `codigos_inmueble` | 74% | Capa 2 (Collection, crítico para filtros de inmueble) |
| `entidades_clave` | 100% | Capa 3 (estructura variable por tipo) |
| `fechas_importantes` | 97% | Capa 3 (lista heterogénea); extraer `fecha_emision` y `fecha_vencimiento` a Capa 2 |
| `vigencia` | 100% | Capa 2 (extraer `fecha_inicio`/`fecha_fin` escalares) |
| `autoridad_emisora` | 55% | Capa 2 (string filtrable) |
| `monto_principal` | 32% | Capa 3 (JSON libre, no todos los docs tienen monto) |
| `metadata_extra` | 100% | Capa 3 (JSON libre por definición) |
| `confianza` | 100% | Capa 1 (diagnóstico de pipeline) |
| `notas` | 100% | Capa 1 (diagnóstico) |

## 5. Patrones de códigos de inmueble

### Modelados por gpt-5-mini (agrupados)

| Código | Apariciones (discovery) |
|---|---|
| `RA03` | 4 |
| `RE05` | 3 |
| `RE05A` | 3 |
| `RA03-INV` | 2 |
| `002-247-009` | 2 |
| `REQ5` | 2 |
| `SLO2-A-YAN-500-20` | 2 |
| `SL02-A-YAN-500-20` | 2 |
| `L-22393` | 1 |
| `BITACORA 2515` | 1 |
| `DICTAMEN 096 TLQ 5 05 E/2019 059` | 1 |
| `DGIT 447/2021` | 1 |
| `Folio Nº 11708` | 1 |
| `310111285008` | 1 |
| `Manzana 10 Lote 8` | 1 |
| `C1SL6C1SO-A1LO-11AA-N1OLI1S-OLF-SOSA1U1U62S1680LCM1LLBU8CL18011B1L-C21-C1UL-A5IBI11N1SI-BLL01CV-SLSUI.L-A1SO-,20FIF3AF||1EV2` | 1 |
| `B-LCI-6-1-43` | 1 |
| `FIDEICOMISO 4058/2020` | 1 |
| `LICENCIA No. 255` | 1 |
| `EXP. 238/066/21US` | 1 |
| `BOULEVARD INDUSTRIA AEROESPACIAL NÚMERO 3301` | 1 |
| `5140-RAMOS ARIZPE` | 1 |
| `Calle Industria Aeroespacial No. 3301` | 1 |
| `Libro COAH, Tipo UI, Volumen 6, Número 2, Año 11` | 1 |
| `SGPA-UARN/0363/COAH/2011` | 1 |

### Validación cruzada: códigos detectados directamente en OCR raw (regex)

| Código | Apariciones en texto plano |
|---|---|
| `FECHA` | 562 |
| `FEDERAL` | 360 |
| `RA03` | 232 |
| `SL04` | 84 |
| `SL04A` | 33 |
| `FEBRERO` | 28 |
| `FERNA` | 23 |
| `FECHAS` | 16 |
| `GUION` | 15 |
| `FERNANDE` | 14 |
| `NAVES` | 12 |
| `FERNANDO` | 9 |
| `FERNAND` | 9 |
| `RE05` | 8 |
| `FELIPE` | 6 |
| `GUA01` | 4 |
| `GUVA` | 3 |
| `GUERRA` | 3 |
| `FEDERICO` | 3 |
| `GULDAL` | 3 |
| `FERNÁ` | 3 |
| `FESTA` | 3 |
| `GUNDO` | 3 |
| `FERNANDI` | 3 |
| `FERNANDA` | 3 |

### Observación de formato

Los códigos siguen prefijos de 2–5 caracteres (`RA`, `RE`, `GUA`, `SL`, `FES`, etc.) seguidos de número. Aparecen tanto en el folder path como embebidos en nombres de archivo y en el texto de licencias/contratos. **Implicación para Capa 2**: `inmueble_codigo` debe ser `Collection(Edm.String)` — un documento puede referirse a varios inmuebles (ej: planos con código genérico + licencia específica).

## 6. Formatos de fecha encontrados (inconsistencia real)

| Formato observado | Ocurrencias |
|---|---|
| D de mes de YYYY | 18 |
| otro/libre | 14 |
| DD/MM/YYYY | 4 |
| Mes D, YYYY | 1 |

**Implicación**: normalizar en ingesta a ISO (`YYYY-MM-DD`) antes de escribir `Edm.DateTimeOffset` al índice. El modelo ya emite `fecha_iso` en su output — usarlo directamente, con fallback a parse del `texto_literal`.

### Ejemplos literales (citas del OCR)

- `ROCA-IAInmuebles__07._Permisos_de_construcci_n__Licencia_de_Construccion_-_GU01-A` → _"VIGENCIA 730 Dias, 20-04-2023"_
- `ROCA-IAInmuebles__07._Permisos_de_construcci_n__Licencia_de_Construccion_RE05A` → _"Fecha: 29 de junio de 2022"_
- `ROCA-IAInmuebles__07._Permisos_de_construcci_n__RA03_LICENCIA_DE_CONSTRUCCION` → _"DE FECHA 12 DE MARZO DE 2021"_
- `ROCA-IAInmuebles__11._Estudio_fase_I_-_Ambiental__EA_FI_RAMOS_ARIZPE_-_Fase_1` → _"Saltillo, Coahuila a 22 de diciembre de 2020"_
- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Arrendatario__1._PODER_DEL_REPRE…` → _"FECHA DE OTORGAMIENTO: 02 DE MARZO DEL 2010."_
- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Arrendatario__1._PODER_REP_LEGAL` → _"ASAMBLEA GENERAL EXTRAORDINARIA CELEBRADA EN FECHA 02 DE SEPTIEMBRE DE 1987."_
- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Contratos__RA03_Contrato_v2_fina…` → _"Con fecha 05 de Julio de 2024"_
- `ROCA-IAInmuebles__33._Constancia_situacion_fiscal__CONSTANCIA_DE_SITUACION_FISCAL_0001` → _"MONTERREY, NUEVO LEON, a 26 de Mayo de 2020"_
- `ROCA-IAInmuebles__33._Constancia_situacion_fiscal__CONSTANCIA_DE_SITUACION_FISCAL_2022` → _"APODACA , NUEVO LEON A 16 DE FEBRERO DE 2022"_
- `ROCA-IAInmuebles__33._Constancia_situacion_fiscal__CONSTANCIA_DE_SITUACION_FISCAL` → _"SAN PEDRO TLAQUEPAQUE , JALISCO A 04 DE OCTUBRE DE 2022"_

## 7. Autoridades emisoras detectadas (para licencias/CSFs)

| Autoridad | Documentos |
|---|---|
| Servicio de Administración Tributaria (SAT) | 4 |
| SAT (Servicio de Administración Tributaria) / SHCP | 2 |
| Gobierno de TLAQUEPAQUE - Dirección de Control de la Edificación / Coordinación General de Gestión Integral de la Ciudad | 1 |
| Municipio de Reynosa, Tamaulipas Secretaría de Obras Públicas, Desarrollo Urbano y Medio Ambiente | 1 |
| Dirección Municipal de Desarrollo Urbano y de Vivienda, Ramos Arizpe, Coahuila | 1 |
| CAI CONSULTORÍA AMBIENTAL INTEGRAL | 1 |
| Secretaría de Relaciones Exteriores (Delegación en Hermosillo, Sonora) | 1 |
| Secretaría de Relaciones Exteriores | 1 |
| Servicio de Administración Tributaria (SAT) - Secretaría de Hacienda y Crédito Público | 1 |
| Notaría Pública No. 11, Hermosillo, Sonora (Lic. Francisco Javier Cabrera Fernández) | 1 |
| Dirección General del Registro Nacional de Población e Identidad (RENAPO) - Secretaría de Gobernación | 1 |
| CFE (Comisión Federal de Electricidad) | 1 |
| SAT (Servicio de Administración Tributaria) - Secretaría de Hacienda y Crédito Público | 1 |
| Notaría Pública No. 151, Ciudad de México (Lic. Cecilio González Márquez) | 1 |
| Dirección Municipal de Desarrollo Urbano del R. Ayuntamiento de Ramos Arizpe, Coah. | 1 |
| CFE | 1 |
| SAT | 1 |

## 8. RFCs detectados (regex directo en OCR)

- **Únicos**: 35
- **Top 5**:
  - `FIA140113TU2` (27 apariciones)
  - `GSE990319JR6` (25 apariciones)
  - `GOMC4911203C0` (24 apariciones)
  - `SSC040816G99` (18 apariciones)
  - `PIM0310036Y0` (17 apariciones)

**Implicación**: los RFCs son datos personales. NO exponerlos en campos `retrievable=true` del índice sin group-trimming. Considerar campo `rfcs_detectados: Collection(Edm.String), retrievable=false` para filtros internos.

## 9. Claves encontradas en `metadata_extra` (Capa 3)

Keys que el modelo propuso para el JSON libre, indicando qué conceptos NO encajan en Capa 2 rígida.

| Key | Apariciones |
|---|---|
| `ubicacion` | 13 |
| `titulo` | 11 |
| `nombre_archivo` | 11 |
| `escala` | 10 |
| `proyecto` | 10 |
| `numero_dibujo` | 7 |
| `superficie_m2` | 6 |
| `idCIF` | 6 |
| `regimen_capital` | 6 |
| `codigo_postal` | 6 |
| `cadena_original_sello` | 6 |
| `no_dibujo` | 6 |
| `observaciones_ocr` | 6 |
| `actividades_economicas` | 5 |
| `tipo_plano` | 5 |
| `uso_suelo` | 4 |
| `colonia` | 4 |
| `municipio` | 4 |
| `telefono` | 4 |
| `observaciones_tecnicas` | 4 |
| `correo_electronico` | 4 |
| `rfc` | 4 |
| `folio` | 3 |
| `clave_catastral` | 3 |
| `paginas` | 3 |
| `numero_escritura` | 3 |
| `nombre_comercial` | 3 |
| `obligaciones` | 3 |
| `entidad_federativa` | 3 |
| `idioma` | 3 |

## 10. Citas literales por tipo de documento (muestra forense)

### `licencia_construccion`

- `ROCA-IAInmuebles__07._Permisos_de_construcci_n__Licencia_de_Construccion_-_GU01-…` → `codigos_inmueble=L-22393`
  > _…UERAGUY USO DEL PREDIO AMPLIACIÓN SERVICIOS VIGENCIA 730 Dias, 20-04-2023 CLAVE L-22393 TLAQUEPAQUE TRAQUEKID NOMBRE DEL PROPIETARIO CALLE/NUMERO OFICIAL COLONIA ENTRE…_
- `ROCA-IAInmuebles__07._Permisos_de_construcci_n__Licencia_de_Construccion_-_GU01-…` → `entidad=propietario:RC. INMUEBLES INDUSTRIALES S.A. DE C.V.`
  > _…sidad alta UBICACION DE LA OBRA TLAQUEPAQUE TLAQUEPAQUE TLAGUEPAQUE TLAQUEPAQUE RC. INMUEBLES INDUSTRIALES S.A. DE C.V. CIRCUITO CEDROS NORTE, 520 LOTE 10 ADVEALQUIL TLAQUEZADU VLAQUEMQUE TLACITEDAĞI…_
- `ROCA-IAInmuebles__07._Permisos_de_construcci_n__Licencia_de_Construccion_RE05A` → `codigos_inmueble=310111285008`
  > _…20FIF3AF||1EV2 Licencia Núm .: 5463 Fecha: 29 de junio de 2022 Clave Catastral: 310111285008 Propietario o Poseedor BANCO ACTINVER, S.A., INSTITUCION DE BANCA MULTIPLE GPO…_

### `estudio_ambiental`

- `ROCA-IAInmuebles__11._Estudio_fase_I_-_Ambiental__EA_FI_RAMOS_ARIZPE_-_Fase_1` → `codigos_inmueble=5140-RAMOS ARIZPE`
  > _…IÓN PROMEDIO ANUAL (MM) La estación meteorológica más cercana al proyecto es la 5140-Ramos Arizpe, la cual cuenta con un registro de la precipitación del año 1980 hasta el 2013.…_
- `ROCA-IAInmuebles__11._Estudio_fase_I_-_Ambiental__EA_FI_RAMOS_ARIZPE_-_Fase_1` → `entidad=elaborador_consultoria:CAI CONSULTORÍA AMBIENTAL INTEGRAL`
  > _…IONES 31 XVII. RESPONSABLE DE LA ELABORACION DEL ESTUDIO. 28 XVIII. GLOSARIO 33 CAI CONSULTORÍA AMBIENTAL INTEGRAL I. OBJETIVO Efectuar una investigación preliminar de las actividades pasadas y…_

### `acta_asamblea`

- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Arrendatario__1._PODER…` → `codigos_inmueble=VOLUMEN 015`
  > _…NOR HERMOSILLO, SONORA Lio. Francisco Javier Cabrera Fernández NEXT TITULAR --- VOLUMEN 015 QUINCE. --- NUMERO 1,442 MIL CUATROCIENTOS CUARENTA Y DOS. - - - EN LA CIUDAD D…_
- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Arrendatario__1._PODER…` → `entidad=sociedad/constituyente/compareciente:SUPPLIER'S CITY, S.A. DE C.V.`
  > _…GDA SANORA SOTELO Y/O SOCORRO YANEZ DURAN. DENUPERWEZGIN .A NOTARIA SMILESUPPLIER'S CITY, S.A. DE C.V. CIUDAD DE PROVEEDORES S.A. DE C.V. SONORA 2. MAKY SUPPLIER'S CITY. S.A. DE C.V. CIUDAD…_

### `escritura_publica`

- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Arrendatario__1._PODER…` → `codigos_inmueble=ESCRITURA PUBLICA NUMERO 27,748`
  > _…" SE AGREGA AL LEGAJO DEL APENDICE, COPIA CERTIFICADA DL In DE OCTUBRE DE 1987. ESCRITURA PUBLICA NUMERO 27,748, VOL. 529, DE FECHA 13 DE MARZO DE 1986, OTORGADA ANTE ESTA MISMA NOFARIA, MEDI…_
- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Arrendatario__1._PODER…` → `entidad=representante_legal / presidente / accionista:SERGIO JESUS MAZON RUBIO`
  > _…DUSTRIALES DE ALTA TECNOLOGIA HERMOSILLO " S.A. DE C.V., POR CONDUCTO DEL SEÑOR SERGIO JESUS MAZON RUBIO, VIENE A QUE SE PROTOCOLICE ACTA DE ASAMBLEA GENERAL EX- TRAORDINARIA CELEBRADA…_

### `contrato_arrendamiento`

- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Contratos__RA03_Contra…` → `codigos_inmueble=RA03-INV`
  > _…atastral 002-247-009, donde está desarrollado el edificio industrial denominado RA03-INV, con un área rentable de 108,943 pies cuadrados (aproximadamente 10,121 metros…_
- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Contratos__RA03_Contra…` → `entidad=Arrendador (fiduciario):BANCO ACTINVER, S.A. INSTITUCIÓN DE BANCA MÚLTIPLE, GRUPO FINANCIERO ACTINVER`
  > _…ONTRATO DE ARRENDAMIENTO celebrado entre LEASE AGREEMENT entered by and between BANCO ACTINVER, S.A. INSTITUCIÓN DE BANCA MÚLTIPLE, GRUPO FINANCIERO ACTINVER, únicamente en su carácter de Fiduciario, en el Contrato de Fideicomiso irrevoc…_

### `constancia_situacion_fiscal`

- `ROCA-IAInmuebles__33._Constancia_situacion_fiscal__CONSTANCIA_DE_SITUACION_FISCA…` → `entidad=contribuyente / persona moral:YANFENG SEATING MEXICO`
  > _…io de Administración Tributaria YSM200512G37 Registro Federal de Contribuyentes YANFENG SEATING MEXICO Nombre, denominación o razón social idCIF: 20050137306 VALIDA TU INFORMACIÓN FI…_
- `ROCA-IAInmuebles__33._Constancia_situacion_fiscal__CONSTANCIA_DE_SITUACION_FISCA…` → `entidad=contribuyente / razón social:ROGERS FOAM MEXICO`
  > _…IO DE ADMINISTRACIÓN TRIBUTARIA RFM030526L6A Registro Federal de Contribuyentes ROGERS FOAM MEXICO Nombre, denominación o razón social idCIF: 15010529513 VALIDA TU INFORMACIÓN FI…_
- `ROCA-IAInmuebles__33._Constancia_situacion_fiscal__CONSTANCIA_DE_SITUACION_FISCA…` → `entidad=contribuyente / persona moral:MAQUIMEX OPERADOR`
  > _…IO DE ADMINISTRACIÓN TRIBUTARIA MOP210705IC6 Registro Federal de Contribuyentes MAQUIMEX OPERADOR Nombre, denominación o razón social idCIF: 21070188730 VALIDA TU INFORMACIÓN FI…_

### `plano_arquitectonico`

- `ROCA-IAInmuebles__65._Planos_arquitectonicos_As_built__100.-_ARQUITECTONICOS_PDF…` → `codigos_inmueble=RA03-FOAM-100-32`
  > _…] [6.23ft] [13.96ft] [13.83Ft [3.40Ft] 3 10 35|ft] 2 9 No. DIBUJO / No. DRAWING RA03-FOAM-100-32 5 190 4.21 1 4.25 2,57 [8.45ft] O 1.06 5.98 GtSport] [10.42ft] 3.18 tilo.24/t 3…_
- `ROCA-IAInmuebles__65._Planos_arquitectonicos_As_built__100.-_ARQUITECTONICOS_PDF…` → `entidad=desarrollador/propietario:ROCA DESARROLLOS`
  > _…RECIBIÓ 0 5. 5 42}}] 2 15 9 1 3 [21.77Ft] 1 DESCRIPCION DESCRIPTION en 3.18ft] ROCA DESARROLLOS 3,66 [4.94at] 1.62 [5.33ft] AS BUILT 2,14 1,5 1 [8.99Ft] [25.55ft] 1 [1.99Ft] 7…_
- `ROCA-IAInmuebles__65._Planos_arquitectonicos_As_built__100.-_ARQUITECTONICOS_PDF…` → `codigos_inmueble=RA03-FOAM-100-33`
  > _…ING.ANGEL CHAVEZ APROBO APPROVED: ARQ.MAYRA MARROQUIN No. DIBUJO / No. DRAWING RA03-FOAM-100-33 PROYECTO / PROJECT ROGERS Foam México S de RL de CV INGENIERIA POR / ENGINEERIN…_

### `escritura_publica_acta_asamblea`

- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__1._SUPPLIER_S_CITY…` → `entidad=sociedad/objeto_acta:SUPPLIER'S CITY, S.A. DE C.V.`
  > _…TERCERA En virtud de dicho reembolso acordado, el Capital Social de la empresa SUPPLIER'S CITY, S.A. DE C.V., desciende a la cantidad de $48,635,000.00 M.N. (cuarenta y un millones seiscie…_

### `constancia_curp`

- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__3.1._CURP_BALR5912…` → `entidad=titular:RUBEN BARAJAS DE LOZA`
  > _…LAVE ÚNICA DE REGISTRO DE POBLACIÓN Clave: BALR591206HDFRZB07 Soy México Nombre RUBEN BARAJAS DE LOZA Entidad de registro: DISTRITO FEDERAL GOBIERNO DE MÉXICO GOBERNACIÓN RENAPO SEC…_

### `recibo_servicio`

- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__3.3._COMPROBANTE_D…` → `codigos_inmueble=520050507762`
  > _…AGO Y BLVD SAN BERNARDO VISTA DEL LAGOC.P.83247 HERMOSILLO,Son. NO. DE SERVICIO:520050507762 RMU:83247 05-01-12 XAXX-010101 001 CFE LÍMITE DE PAGO:12 JUN 24 CORTE A PARTIR:…_
- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__3.3._COMPROBANTE_D…` → `entidad=emisora_suministrador:CFE Comisión Federal de Electricidad`
  > _…CFE Comisión Federal de Electricidad® CFE Suministrador de Servicios Básicos Río Ródano No. 14, colonia Cuauhtémoc,…_

### `contrato_compraventa`

- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__ACTINVER_P03RA03_J…` → `codigos_inmueble=RA03`
  > _…EZ NOTARIO PUBLICO NUM. 151 CIUDAD DE MÉXICO PROYECTO R5 - OPAL - COMPRAVENTA - RA03 - COAHUILA - RAMOS ARIZPE - 1 INM LIBRO NÚMERO CINCO MIL SEISCIENTOS CINCUENTA…_
- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__ACTINVER_P03RA03_J…` → `entidad=vendedor (fiduciario) / vendedor en escritura:BANCA MIFEL, S.A., INSTITUCIÓN DE BANCA MÚLTIPLE, GRUPO FINANCIERO MIFEL`
  > _…INISTRACIÓN DE INMUEBLES CON DERECHOS DE REVERSIÓN NÚMERO 1349, como Comprador, BANCA MIFEL, S.A., INSTITUCIÓN DE BANCA MÚLTIPLE, GRUPO FINANCIERO MIFEL, ÚNICA Y EXCLUSIVAMENTE EN SU CALIDAD DE FIDUCIARIA, (i) DEL FIDEICOMISO IDENTI…_

### `estados_financieros_auditados`

- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__Estados_Financiero…` → `codigos_inmueble=Henry Ford`
  > _…os, y gastos de arrendamiento, debido a que se rentaron dos naves industriales "Henry Ford" y "Silao", lo anterior por el incremento de las operaciones de su parte relaci…_
- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__Estados_Financiero…` → `entidad=entidad auditada / emisora:Supplier's City, S.A. de C.V.`
  > _…SUPPLIER'S CITY, S.A. DE C.V. Estados Financieros Al 31 de diciembre de 2022 y 2021 (Con el Informe de los Au…_

### `constancia_uso_suelo`

- `ROCA-IAInmuebles__Principal__ACTINVER_P03RA03_Gestoria_LicenciaDeUsoDeSuelo` → `codigos_inmueble=FIDEICOMISO NO. 4058/2020`
  > _…ANCIA BANCA MIFEL, S.A., INSTITUCION DE BANCA MULTIPLE, GRUPO FINANCIERO MIFEL, FIDEICOMISO NO. 4058/2020. Av. San Jerónimo No. 370. Colonia San Jerónimo. Monterrey, Nuevo León. 16 de a…_
- `ROCA-IAInmuebles__Principal__ACTINVER_P03RA03_Gestoria_LicenciaDeUsoDeSuelo` → `entidad=autoridad_emisora:Dirección Municipal de Desarrollo Urbano del R. Ayuntamiento de Ramos Arizpe, Coah.`
  > _…RAMOS ES MÁS DIRECCIÓN MUNICIPAL DE DESARROLLO URBANO DEL R. AYUNTAMIENTO DE RAMOS ARIZPE, COAH. OFICIO: 7 3 6. SOL/EXP. 1052/379/22US ASUNTO: CONSTANCIA BANCA MIFEL, S.A., INS…_

### `factura_electronica`

- `ROCAIA-INMUEBLESV2__FESWORLD__P03-RA03_30._Contrato_de_arrendamiento_y_anexos_0.…` → `entidad=emisor:TELEFONOS DE MEXICO S.A.B. DE C.V.`
  > _…1 de 5 Cuenta Maestra CARATULA TELEFONOS DE MEXICO S.A.B. DE C.V. PARQUE VIA 198 COL CUAUHTEMOC C.P. 06500 Ciudad de Mexico RFC: TME840315KT6 DAT…_

### `estudio_geotecnico`

- `ROCAIA-INMUEBLESV2__FESWORLD__P03-RA03_53._Dise_o_de_pavimentos__DISE_O_DE_PAVIM…` → `codigos_inmueble=RA03`
  > _…PRUEBAS Y RESISTENCIA EN CONCRETO S.A DE C.V. REF .: PPYR-F-07-19-144/064 NAVE RA03 Hoja 1 de 76 A 20 de Septiembre Del 2019. At'n: ROCA DESARROLLOS Presente. - No…_
- `ROCAIA-INMUEBLESV2__FESWORLD__P03-RA03_53._Dise_o_de_pavimentos__DISE_O_DE_PAVIM…` → `entidad=cliente / agencia:ROCA DESARROLLOS`
  > _…PPYR-F-07-19-144/064 NAVE RA03 Hoja 1 de 76 A 20 de Septiembre Del 2019. At'n: ROCA DESARROLLOS Presente. - Nos permitimos presentar a su atenta consideración las propuestas d…_

### `contrato_desarrollo_inmobiliario`

- `ROCAIA-INMUEBLESV2__FESWORLD__P06_-_RE05AINV-HCP_04._Actas_constitutivas_del_pro…` → `codigos_inmueble=4974`
  > _…anexo forma parte integral del contrato de fideicomiso de administración número 4974 celebrado el día 7 de mayo de 2021 entre (i) Banco Invex, S.A., Institución de…_
- `ROCAIA-INMUEBLESV2__FESWORLD__P06_-_RE05AINV-HCP_04._Actas_constitutivas_del_pro…` → `entidad=Cliente / Fiduciario:Banco Actinver, S.A., Institución de Banca Múltiple, Grupo Financiero Actinver`
  > _…rrollador y Administrador, según el contexto del Fideicomiso lo requiera, y (v) Banco Actinver, S.A., Institución de Banca Múltiple, Grupo Financiero Actinver, en carácter de Fiduciario. D. CONTRATO DE DESARROLLO INMOBILIARIO CELEBRADO EN…_

### `garantia_corporativa`

- `ROCAIA-INMUEBLESV2__FESWORLD__P4-SL02-INV-YANFENG_29._Garantia_corportativa_depo…` → `codigos_inmueble=Lote 10`
  > _…er the "Building") at The Building's addresses are (a) Carrusel Cuatro St. #108 Lote 10, Laguna de San Vicente in the Logistik I Industrial Park (the “Industrial Park"…_
- `ROCAIA-INMUEBLESV2__FESWORLD__P4-SL02-INV-YANFENG_29._Garantia_corportativa_depo…` → `entidad=garante:YANFENG USA AUTOMOTIVE TRIM SYSTEMS, INC.`
  > _…EXHIBIT F CORPORATE GUARANTY YANFENG USA AUTOMOTIVE TRIM SYSTEMS, INC. a corporation duly organized and existing under the laws of the United States o…_

## 11. Tabla por documento (resumen individual)

| PDF (stem abreviado) | Carpeta canónica | tipo detectado | confianza | #códigos | vigencia? | monto? | #entidades |
|---|---|---|---|---|---|---|---|
| `ROCA-IAInmuebles__07._Permisos_de_construcci_n__Li…` | `07._Permisos_de_construcc` | `licencia_construccion` | media | 5 | ✓ | ✓ | 5 |
| `ROCA-IAInmuebles__07._Permisos_de_construcci_n__Li…` | `07._Permisos_de_construcc` | `licencia_construccion` | alta | 4 | ✓ | ✓ | 5 |
| `ROCA-IAInmuebles__07._Permisos_de_construcci_n__RA…` | `07._Permisos_de_construcc` | `licencia_construccion` | alta | 4 | ✓ | ✓ | 6 |
| `ROCA-IAInmuebles__11._Estudio_fase_I_-_Ambiental__…` | `11._Estudio_fase_I_-_Ambi` | `estudio_ambiental` | alta | 6 | — | — | 8 |
| `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_…` | `30._Contrato_de_arrendami` | `acta_asamblea` | alta | 13 | ✓ | ✓ | 17 |
| `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_…` | `30._Contrato_de_arrendami` | `escritura_publica` | alta | 18 | ✓ | ✓ | 12 |
| `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_…` | `30._Contrato_de_arrendami` | `contrato_arrendamiento` | alta | 2 | ✓ | ✓ | 9 |
| `ROCA-IAInmuebles__33._Constancia_situacion_fiscal_…` | `33._Constancia_situacion_` | `constancia_situacion_fiscal` | alta | 0 | — | — | 3 |
| `ROCA-IAInmuebles__33._Constancia_situacion_fiscal_…` | `33._Constancia_situacion_` | `constancia_situacion_fiscal` | alta | 0 | — | — | 3 |
| `ROCA-IAInmuebles__33._Constancia_situacion_fiscal_…` | `33._Constancia_situacion_` | `constancia_situacion_fiscal` | alta | 0 | — | — | 2 |
| `ROCA-IAInmuebles__33._Constancia_situacion_fiscal_…` | `33._Constancia_situacion_` | `constancia_situacion_fiscal` | alta | 0 | — | — | 3 |
| `ROCA-IAInmuebles__65._Planos_arquitectonicos_As_bu…` | `65._Planos_arquitectonico` | `plano_arquitectonico` | alta | 2 | — | — | 8 |
| `ROCA-IAInmuebles__65._Planos_arquitectonicos_As_bu…` | `65._Planos_arquitectonico` | `plano_arquitectonico` | alta | 11 | — | — | 7 |
| `ROCA-IAInmuebles__65._Planos_arquitectonicos_As_bu…` | `65._Planos_arquitectonico` | `plano_arquitectonico` | alta | 3 | — | — | 7 |
| `ROCA-IAInmuebles__65._Planos_arquitectonicos_As_bu…` | `65._Planos_arquitectonico` | `plano_arquitectonico` | alta | 1 | — | — | 7 |
| `ROCA-IAInmuebles__65._Planos_arquitectonicos_As_bu…` | `65._Planos_arquitectonico` | `plano_arquitectonico` | alta | 3 | — | — | 8 |
| `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_co…` | `Biblioteca_de_suspensione` | `escritura_publica_acta_asamblea` | alta | 0 | ✓ | ✓ | 16 |
| `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_co…` | `Biblioteca_de_suspensione` | `constancia_curp` | alta | 0 | — | — | 5 |
| `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_co…` | `Biblioteca_de_suspensione` | `constancia_situacion_fiscal` | alta | 0 | — | — | 3 |
| `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_co…` | `Biblioteca_de_suspensione` | `recibo_servicio` | alta | 9 | ✓ | ✓ | 5 |
| `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_co…` | `Biblioteca_de_suspensione` | `constancia_situacion_fiscal` | alta | 0 | — | — | 3 |
| `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_co…` | `Biblioteca_de_suspensione` | `constancia_situacion_fiscal` | alta | 0 | ✓ | — | 5 |
| `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_co…` | `Biblioteca_de_suspensione` | `contrato_compraventa` | alta | 10 | — | ✓ | 12 |
| `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_co…` | `Biblioteca_de_suspensione` | `estados_financieros_auditados` | alta | 3 | ✓ | ✓ | 9 |
| `ROCA-IAInmuebles__Principal__ACTINVER_P03RA03_Gest…` | `Principal` | `constancia_uso_suelo` | alta | 5 | ✓ | — | 7 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P03-CJ03A-INV_66._Pl…` | `FESWORLD` | `plano_arquitectonico` | alta | 24 | — | — | 6 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P03-RA03_30._Contrat…` | `FESWORLD` | `factura_electronica` | alta | 0 | — | ✓ | 6 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P03-RA03_53._Dise_o_…` | `FESWORLD` | `estudio_geotecnico` | alta | 23 | ✓ | — | 5 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P03-RA03_62._Ingenie…` | `FESWORLD` | `plano_arquitectonico` | alta | 4 | — | — | 6 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P06_-_RE05AINV-HCP_0…` | `FESWORLD` | `contrato_desarrollo_inmobiliario` | alta | 5 | ✓ | ✓ | 7 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P06_-_RE05AINV-HCP_6…` | `FESWORLD` | `plano_arquitectonico` | alta | 7 | — | — | 6 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P06_-_RE05AINV-HCP_6…` | `FESWORLD` | `plano_arquitectonico` | alta | 5 | — | — | 6 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P06_-_RE05AINV-HCP_6…` | `FESWORLD` | `plano_arquitectonico` | alta | 4 | — | — | 6 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P4-GU01A-TEN-_MINGLI…` | `FESWORLD` | `constancia_situacion_fiscal` | alta | 3 | — | — | 3 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P4-SL02-INV-YANFENG_…` | `FESWORLD` | `garantia_corporativa` | alta | 8 | ✓ | — | 5 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P4-SL02-INV-YANFENG_…` | `FESWORLD` | `plano_arquitectonico` | alta | 3 | — | — | 7 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P4-SL02-INV-YANFENG_…` | `FESWORLD` | `plano_arquitectonico` | alta | 3 | — | — | 8 |
| `ROCAIA-INMUEBLESV2__FESWORLD__P4-SL02-INV-YANFENG_…` | `FESWORLD` | `plano_arquitectonico` | alta | 3 | — | — | 7 |

## 12. Sesgos conocidos de la muestra

- La muestra se limitó a PDFs ≤50 MB para rapidez — contratos escaneados muy grandes (como el de Arrendamiento Minglida de 101 MB visto en el smoke test) **no fueron procesados**. Implicación: Fase 5 debe aumentar el límite de Document Intelligence o usar compressed OCR.
- Site 2 (`ROCAIA-INMUEBLESV2`) solo aportó 5 docs, todos del folder `FESWORLD`, predominantemente planos. Subrepresentación de contratos del site 2.
- La carpeta `11. Estudio fase I - Ambiental` solo tenía 1 PDF elegible en la raíz de ROCA-IAInmuebles — 1 muestra es insuficiente para decidir campos específicos de estudios ambientales.

## 13. Inconsistencias detectadas (lista para decidir)

- **Códigos de inmueble** con y sin guion/sufijo alfa (`RA03` vs `RA03-FOAM`) — decisión: normalizar a prefijo base + sufijo opcional, o almacenar el literal y indexar ambos.
- **Nombres de autoridad emisora** varían entre siglas (`SAT`) y nombre completo (`Servicio de Administración Tributaria`) — decisión: normalizar con diccionario pequeño o dejar como `Edm.String` libre.
- **RFCs** aparecen con y sin espacios — normalizar a uppercase sin espacios antes de indexar.

## 14. Duplicación masiva en SharePoint — hallazgo crítico

**7 de 45 PDFs (16%) son duplicados exactos por hash** — el mismo archivo físico subido a múltiples carpetas/drives con nombres distintos. Esto es información real y valiosa del dataset de producción de ROCA.

### Grupos de duplicados detectados

**Grupo 1** (`hash=0595380bfc37…`, 2 copias):
- `ROCA-IAInmuebles__07._Permisos_de_construcci_n__RA03_LICENCIA_DE_CONSTRUCCION` ← canonical
- `ROCA-IAInmuebles__Documentos_semantica_copilot__7-ELEVEN_CLTXX170_GESTORIA_PERMISO_DE_CONSTRUCC…`

**Grupo 2** (`hash=ba78ac3018c8…`, 3 copias):
- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Arrendatario__1._PODER_DEL_REPRESENTA…` ← canonical
- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__ODER_DEL_REPRESENTANTE_LEGAL_RBL_…`
- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__ODER_DEL_REPRESENTANTE_LEGAL_RBL_…`

**Grupo 3** (`hash=f57a8ac63e79…`, 2 copias):
- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Arrendatario__1._PODER_REP_LEGAL` ← canonical
- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__1._PODER_REP_LEGAL_2A93BDE2-C7E0-…`

**Grupo 4** (`hash=85ed00c9f657…`, 2 copias):
- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Contratos__RA03_Contrato_v2_final` ← canonical
- `ROCA-IAInmuebles__30._Contrato_de_arrendamiento_y_anexos__Supliers_City_Contrato_Fully_Executed`

**Grupo 5** (`hash=0e88b58a2ed0…`, 3 copias):
- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__ACTINVER_P03RA03_Juridico_TituloD…` ← canonical
- `ROCA-IAInmuebles__Biblioteca_de_suspensiones_de_conservaci_n__RA03_FD703844-F12B-42B5-94E5-D37D…`
- `ROCA-IAInmuebles__Principal__ACTINVER_P03RA03_Juridico_TituloDePropiedad_05012026`

### Implicaciones para el schema y la ingesta de producción

1. **`nombre_archivo` y `sharepoint_url` NO son identificadores confiables del documento lógico** — el mismo archivo físico puede tener nombres radicalmente distintos en distintas carpetas (ej: `7-ELEVEN_CLTXX170_GESTORIA_PERMISO` y `RA03_LICENCIA_DE_CONSTRUCCION` son el mismo PDF).
2. **Agregar campo `content_hash: Edm.String` en Capa 1** como identificador canónico del documento lógico. `parent_document_id` debe derivarse del `content_hash`, no del path de SharePoint.
3. **Fase 5 (Logic App) debe hacer dedup por hash en la ingesta**: antes de re-OCRear, calcular el hash del PDF y verificar si ya existe en el índice. Si existe, agregar el nuevo `sharepoint_url` como un path alternativo al mismo documento lógico, no crear un doc nuevo.
4. **Ahorro estimado en producción**: si la tasa de duplicación del 16% se mantiene en los ~10K docs totales, Fase 5 puede evitar ~1555 re-OCRs ≈ $30-50 USD por corrida inicial y almacenamiento redundante.
5. **Agregar campo `alternative_urls: Collection(Edm.String), retrievable=true` en Capa 1** (o en Capa 3 si se prefiere) para preservar todas las ubicaciones del documento en SharePoint — útil para R-10 (citación exacta) cuando el usuario pida "dónde está este documento" y haya múltiples respuestas válidas.
