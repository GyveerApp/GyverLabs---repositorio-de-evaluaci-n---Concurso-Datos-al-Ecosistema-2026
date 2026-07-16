# Arquitectura — GyverLabs

Documento de soporte técnico para el jurado del Concurso Datos al Ecosistema 2026.
Ver [`LICENSE`](../LICENSE) — este material se comparte únicamente con fines de evaluación.

## 1. Modelo multi-tenant

Un servidor sirve N colegios. Cada colegio tiene su propio schema lógico en PostgreSQL,
su propio subdominio y su propia identidad visual, pero comparte el mismo motor de
aplicación y el mismo motor de IA.

```mermaid
flowchart TB
    subgraph Publico["Schema 'public' (global)"]
        T[(tenants)]
        P[(planes)]
        SA[(super_admins)]
    end

    subgraph TenantA["Schema 'colegio_a'"]
        UA[(usuarios)]
        AA[(académico)]
        ASA[(asistencia)]
        SRDA[(srd_scores)]
        CA[(contabilidad_fse)]
    end

    subgraph TenantB["Schema 'colegio_b'"]
        UB[(usuarios)]
        AB[(académico)]
        ASB[(asistencia)]
        SRDB[(srd_scores)]
        CB[(contabilidad_fse)]
    end

    Middleware["core/tenant.py<br/>detecta tenant por header Host<br/>y fija el search_path"] --> TenantA
    Middleware --> TenantB
    T --> Middleware
```

## 2. Los cuatro módulos dentro de cada colegio

```mermaid
flowchart LR
    A[Módulo A<br/>Asistencia y Alertas] --> D[Motor SRD<br/>Score de Riesgo]
    B[Módulo B<br/>Aula Virtual Coordinada]
    C[Módulo C<br/>Contabilidad FSE]
    E[Agente IA<br/>Orientación Estudiantil]

    D --> Tablero[Tablero del Coordinador<br/>mapa de calor + alertas]
    B --> Tablero
    C --> Reportes[Reportes Secretaría<br/>de Educación]
    E --> Familias[Estudiantes y Familias<br/>WhatsApp / Web]
```

## 3. Actores y permisos

| Actor | Alcance |
|---|---|
| Super Admin | Gestiona todos los tenants y secretarías desde un panel global |
| Admin Secretaría | Ve agregados departamentales: mapa de riesgo, FSE consolidado, reportes MEN |
| Rector / Coordinador | Panel del colegio: alertas SRD, aprobación de planes, contabilidad FSE |
| Docente | Registra asistencia, sube material del aula virtual, califica |
| Estudiante / Familia | Consulta notas, asistencia, material y habla con el agente IA |

## 4. Fases de construcción

```mermaid
flowchart LR
    F1[Fase 1<br/>Núcleo multi-tenant<br/>+ autenticación] --> F2[Fase 2<br/>Asistencia + Alertas]
    F2 --> F3[Fase 3<br/>Aula Virtual]
    F3 --> F4[Fase 4<br/>Motor SRD + IA]
    F4 --> F5[Fase 5<br/>Contabilidad FSE<br/>+ Portal Secretaría]
```

## 5. Qué se protege y por qué

La estructura completa de rutas, modelos y flujos descrita arriba es real y corresponde
a la implementación de producción. Los siguientes componentes se mantienen fuera de este
repositorio público, por ser el activo diferenciador del producto:

- Pipeline de entrenamiento y pesos del modelo LightGBM del SRD
- Reglas de calibración de umbrales por institución
- Lógica exacta de cruce con fuentes de datos abiertas (SISBÉN IV, SIMAT, DANE, SECOP II)
- Prompts y lógica de orquestación del Agente IA de Orientación Estudiantil

Estos componentes están disponibles para revisión ampliada bajo acuerdo de
confidencialidad institucional (MinTIC, Secretarías de Educación, jurado del concurso).
