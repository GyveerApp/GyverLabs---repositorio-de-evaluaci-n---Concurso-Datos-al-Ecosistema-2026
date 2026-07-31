# Cómo publicar esto en GitHub hoy (guía rápida, solo para ti — no la subas)

1. **Crea el repositorio en GitHub** (botón "New repository"). Nómbralo, por ejemplo,
   `gyverlabs-sistema-educativo` — **NO marques "Public" todavía si quieres revisarlo
   primero**, puedes dejarlo privado, revisar, y luego pasarlo a público.

2. **Revisa antes de subir:**
   - Reemplaza en `README.md` la sección 6 con el enlace real de tu demo/video si ya lo tienes.
   - Confirma que ningún archivo `.env` real (con contraseñas verdaderas) esté en la carpeta.
     El `.gitignore` ya lo bloquea, pero revisa manualmente.
   - Si tienes capturas de pantalla reales del sistema funcionando, agrégalas en una
     carpeta `docs/screenshots/` y enlázalas desde el README — esto suma muchísimo
     ante el jurado.

3. **Sube el proyecto:**
   ```bash
   cd gyverlabs-showcase
   git init
   git add .
   git commit -m "GyverLabs - repositorio de evaluación - Concurso Datos al Ecosistema 2026"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/gyverlabs-sistema-educativo.git
   git push -u origin main
   ```

4. **Pon el repo en público** cuando estés conforme, y copia el enlace para reportarlo
   en el formulario del concurso (recuerda: el requisito según los términos de
   referencia es reportar el enlace del repositorio, no necesariamente tenerlo
   público desde el día uno de desarrollo — revisa el PDF de Términos de Referencia
   para confirmar si piden "público" explícitamente o solo "accesible para evaluación").

5. **Guarda tu código completo real en un repo privado aparte** (o simplemente no lo
   subas a ningún lado público). Este repo de evaluación referencia esa versión
   completa en el README y la LICENSE, dejando constancia de que existe y de que
   tú eres su autor.

6. **Opcional pero recomendado:** sube un ZIP con el código completo real a un
   servicio con timestamp verificable (por ejemplo, un commit privado en GitHub,
   o un registro en la Dirección Nacional de Derecho de Autor de Colombia) *antes*
   de publicar el repo de evaluación. Así tienes evidencia de que la versión
   completa existía primero.
