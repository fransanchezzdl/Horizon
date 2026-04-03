const API_BASE = window.API_BASE;

// Estado global de la academia
let estadoCurso = {
    id_curso: null,
    diapositivas: [],
    progreso: null,
    visitadas: new Set(), // Almacena IDs de diapositivas ya visitadas
    currentDiapositivaIndex: 0,
};

let totalCursos = 0;
let cursosCompletados = 0;

function initAcademiaPage() {
    // ============================================
    // INICIALIZACIÓN DEL CHATBOT
    // ============================================
    const chatAsesor = document.getElementById('chatAsesor');
    const chatHeader = chatAsesor.querySelector('.advisor-header');
    const sendBtn = document.getElementById('sendMsg');
    const chatInput = chatAsesor.querySelector('input');
    const chatContainer = chatAsesor.querySelector('.chat-container');

    // Función para minimizar / maximizar
    if (chatHeader) {
        chatHeader.addEventListener('click', () => {
            chatAsesor.classList.toggle('collapsed');
        });
    }

    // Envío de mensajes
    if (sendBtn && chatInput) {
        sendBtn.addEventListener('click', () => {
            const mensaje = chatInput.value.trim();
            if (mensaje !== "" && !sendBtn.disabled) {
                enviarMensaje(mensaje, chatInput, chatContainer, sendBtn);
            }
        });

        // También permitir envío con Enter
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !sendBtn.disabled) {
                const mensaje = chatInput.value.trim();
                if (mensaje !== "") {
                    enviarMensaje(mensaje, chatInput, chatContainer, sendBtn);
                }
            }
        });
    }

    // ============================================
    // INICIALIZACIÓN DE CURSOS
    // ============================================
    cargarCursos();

    // Event listeners del modal
    const btnCerrarModal = document.getElementById('btn-cerrar-modal');
    if (btnCerrarModal) {
        btnCerrarModal.addEventListener('click', cerrarModal);
    }

    // Botones de navegación
    const btnAnterior = document.getElementById('btn-anterior');
    const btnSiguiente = document.getElementById('btn-siguiente');

    if (btnAnterior) {
        btnAnterior.addEventListener('click', retrocederDiapositiva);
    }

    if (btnSiguiente) {
        btnSiguiente.addEventListener('click', avanzarDiapositiva);
    }
}

// ================================================================
// FUNCIONES DE CURSOS
// ================================================================

/**
 * Carga la lista de cursos y los renderiza en el grid
 */
async function cargarCursos() {
    console.log('[CURSOS] Cargando lista de cursos...');

    try {
        const response = await window.fetchWithAuth(`${API_BASE}/cursos`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            console.error('[CURSOS] Error:', response.status);
            mostrarErrorCursos('Error al cargar los cursos');
            return;
        }

        const cursos = await response.json();
        totalCursos = cursos.length;

        console.log(`[CURSOS] ${cursos.length} cursos cargados`);

        renderizarGridCursos(cursos);

        // --- ¡NUEVO! Cargar el resumen global de progreso ---
        const resumenRes = await window.fetchWithAuth(`${API_BASE}/cursos/resumen/progreso`, { method: 'GET' });
        if (resumenRes.ok) {
            const resumenData = await resumenRes.json();
            cursosCompletados = resumenData.cursos_completados;
            renderizarProgresoGlobal(); // Pintamos la barra con los datos reales
        }
    } catch (err) {
        console.error('[CURSOS] Error de conexión:', err);
        mostrarErrorCursos(`Error de conexión: ${err.message}`);
    }
}

/**
 * Renderiza el grid de cursos disponibles
 */
function renderizarGridCursos(cursos) {
    const grid = document.getElementById('cursos-grid');
    if (!grid) return;

    grid.innerHTML = ''; // Limpiar

    cursos.forEach(curso => {
        const card = document.createElement('a');
        card.className = 'card';
        card.href = '#';
        card.onclick = (e) => {
            e.preventDefault();
            abrirCurso(curso.id_curso || curso.id);
        };

        card.innerHTML = `
            <div class="card-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2l-5.5 9h11z M17.5 13c1.93 0 3.5 1.57 3.5 3.5S19.43 20 17.5 20 14 18.43 14 16.5s1.57-3.5 3.5-3.5z M3 13.5h8v8H3z"/>
                </svg>
            </div>
            <div class="card-icon-hero" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2l-5.5 9h11z M17.5 13c1.93 0 3.5 1.57 3.5 3.5S19.43 20 17.5 20 14 18.43 14 16.5s1.57-3.5 3.5-3.5z M3 13.5h8v8H3z"/>
                </svg>
            </div>
            <h3 class="opt-title">${curso.titulo}</h3>
            <p class="opt-info">${curso.descripcion || 'Sin descripción'}</p>
            <span class="card-link">Acceder al curso →</span>
        `;

        grid.appendChild(card);
    });
}

/**
 * Abre y renderiza un curso (modal carrusel)
 */
async function abrirCurso(idCurso) {
    console.log(`[CURSOS] Abriendo curso ${idCurso}...`);

    try {
        // Fetch del detalle del curso
        const response = await window.fetchWithAuth(`${API_BASE}/cursos/${idCurso}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            console.error(`[CURSOS] Error al abrir curso: ${response.status}`);
            mostrarErrorCursos(`No se pudo abrir el curso`);
            return;
        }

        const cursoData = await response.json();
        
        // Obtener progreso
        const progResponse = await window.fetchWithAuth(`${API_BASE}/cursos/${idCurso}/progreso`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        let progreso = null;
        let indexInicio = 0; // Por defecto a la 1ª

        if (progResponse.ok) {
            progreso = await progResponse.json();
            // Retomar donde lo dejó (diapositiva_alcanzada es 1-based, index es 0-based)
            if (progreso && progreso.diapositiva_alcanzada > 1) {
                // Si completó el curso, lo dejamos en la primera pág para que lo repase (o en la última, como prefieras)
                // En este caso lo llevamos a la última que alcanzó
                indexInicio = progreso.diapositiva_alcanzada - 1;
            }
        }

        // Actualizar estado
        estadoCurso.id_curso = idCurso;
        // Dependiendo de FastAPI, el ID podría venir como cursoData.id o cursoData.id_curso. Usamos fallback:
        const cursoIdReal = cursoData.id_curso || cursoData.id; 
        estadoCurso.diapositivas = cursoData.diapositivas || [];
        estadoCurso.progreso = progreso;
        estadoCurso.visitadas = new Set(); 

        // ¡NUEVO! Pre-llenar las visitadas con su progreso histórico
        if (progreso && progreso.diapositiva_alcanzada > 0) {
            for (let i = 0; i < progreso.diapositiva_alcanzada; i++) {
                if (estadoCurso.diapositivas[i]) {
                    estadoCurso.visitadas.add(estadoCurso.diapositivas[i].id);
                }
            }
        }

        estadoCurso.currentDiapositivaIndex = indexInicio;

        console.log(`[CURSOS] Curso abierto: ${cursoData.titulo}, retomando en índice ${indexInicio}`);

        // Renderizar modal
        abrirModal(cursoData.titulo);

        // Mostrar la diapositiva correspondiente
        mostrarDiapositiva(indexInicio);

        // Si el curso ya estaba completado, mostramos el cartel de una vez
        if (progreso && progreso.completado) {
            mostrarCompletado();
        }

    } catch (err) {
        console.error('[CURSOS] Error:', err);
        mostrarErrorCursos(`Error: ${err.message}`);
    }
}

/**
 * Abre el modal del carrusel
 */
function abrirModal(titulo) {
    const modal = document.getElementById('curriculum-modal');
    const modalTitulo = document.getElementById('modal-titulo-curso');

    if (modal && modalTitulo) {
        modalTitulo.textContent = titulo;
        modal.style.display = 'flex';
    }
}

/**
 * Cierra el modal del carrusel
 */
function cerrarModal() {
    const modal = document.getElementById('curriculum-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Muestra una diapositiva específica
 */
function mostrarDiapositiva(index) {
    if (index < 0 || index >= estadoCurso.diapositivas.length) return;

    const diapositiva = estadoCurso.diapositivas[index];
    estadoCurso.currentDiapositivaIndex = index;

    // Actualizar contenido
    const contenidoDiv = document.getElementById('contenido-diapositiva');
    if (contenidoDiv) {
        contenidoDiv.innerHTML = formatearContenidoDiapositiva(diapositiva.contenido);
    }

    // Actualizar contador
    document.getElementById('diapositiva-actual').textContent = index + 1;
    document.getElementById('diapositivas-total').textContent = estadoCurso.diapositivas.length;

    // Actualizar estado de botones
    actualizarBotones();

    // Detectar si es 1ª visita a esta diapositiva
    const diapositivaId = diapositiva.id;
    const esPrimeraVisita = !estadoCurso.visitadas.has(diapositivaId);

    if (esPrimeraVisita) {
        // Mostrar timer
        iniciarTimer();
    } else {
        // No mostrar timer
        ocultarTimer();
        // Habilitar botones inmediatamente
        document.getElementById('btn-anterior').disabled = index === 0;
        document.getElementById('btn-siguiente').disabled = index === estadoCurso.diapositivas.length - 1;
    }

    // Ocultar indicador de completado
    const completadoIndicator = document.getElementById('completado-indicator');
    if (completadoIndicator) {
        completadoIndicator.style.display = 'none';
    }
}

/**
 * Inicia el timer de 5 segundos para 1ª visita
 */
function iniciarTimer() {
    const timerIndicator = document.getElementById('timer-indicator');
    const timerBar = document.querySelector('.timer-bar');
    const btnAnterior = document.getElementById('btn-anterior');
    const btnSiguiente = document.getElementById('btn-siguiente');

    if (!(timerIndicator && timerBar)) return;

    // Limpiar temporizador previo si existiera
    if (window._academiaTimerId) {
        clearTimeout(window._academiaTimerId);
    }

    timerIndicator.classList.add('active');
    timerBar.style.transition = 'none';
    timerBar.style.width = '0%';
    void timerBar.offsetWidth;

    if (btnAnterior) btnAnterior.disabled = true;
    if (btnSiguiente) btnSiguiente.disabled = true;

    timerBar.style.transition = 'width 5s linear';
    timerBar.style.width = '100%';

    window._academiaTimerId = setTimeout(() => {
        ocultarTimer();

        const index = estadoCurso.currentDiapositivaIndex;
        if (btnAnterior) btnAnterior.disabled = index === 0;
        if (btnSiguiente) btnSiguiente.disabled = index === estadoCurso.diapositivas.length - 1;

        const diapositivaId = estadoCurso.diapositivas[index]?.id;
        if (diapositivaId !== undefined) {
            estadoCurso.visitadas.add(diapositivaId);
        }

        console.log(`[TIMER] Completado para diapositiva ${index + 1}`);
    }, 5000);
}

/**
 * Oculta el timer
 */
function ocultarTimer() {
    const timerIndicator = document.getElementById('timer-indicator');
    const timerBar = document.querySelector('.timer-bar');

    if (window._academiaTimerId) {
        clearTimeout(window._academiaTimerId);
        window._academiaTimerId = null;
    }

    if (timerIndicator) {
        timerIndicator.classList.remove('active');
    }

    if (timerBar) {
        timerBar.style.transition = 'none';
        timerBar.style.width = '0%';
    }
}

/**
 * Avanza a la siguiente diapositiva
 */
function avanzarDiapositiva() {
    const nextIndex = estadoCurso.currentDiapositivaIndex + 1;

    if (nextIndex < estadoCurso.diapositivas.length) {
        mostrarDiapositiva(nextIndex);

        // ¡NUEVO! Solo guardamos en BD si supera su récord personal
        const nuevaPaginaNumero = nextIndex + 1;
        const recordActual = estadoCurso.progreso ? estadoCurso.progreso.diapositiva_alcanzada : 0;
        
        if (nuevaPaginaNumero > recordActual) {
            guardarProgreso(nuevaPaginaNumero);
        }
        
    } else if (nextIndex === estadoCurso.diapositivas.length) {
        // Última diapositiva alcanzada (clic en finalizar)
        mostrarCompletado();
        
        // Aseguramos que se guarde el 100% solo si no estaba completado
        if (!estadoCurso.progreso || !estadoCurso.progreso.completado) {
            guardarProgreso(nextIndex); 
        }
    }
}

function retrocederDiapositiva() {
    const prevIndex = estadoCurso.currentDiapositivaIndex - 1;

    if (prevIndex >= 0) {
        mostrarDiapositiva(prevIndex);
        //No guardamos progreso al ir hacia atrás para no borrar su récord
    }
}

/**
 * Actualiza el estado de los botones de navegación
 */
function actualizarBotones() {
    const btnAnterior = document.getElementById('btn-anterior');
    const btnSiguiente = document.getElementById('btn-siguiente');
    const isFirstSlide = estadoCurso.currentDiapositivaIndex === 0;
    const isLastSlide = estadoCurso.currentDiapositivaIndex === estadoCurso.diapositivas.length - 1;

    if (btnAnterior) {
        btnAnterior.disabled = isFirstSlide;
    }

    if (btnSiguiente) {
        btnSiguiente.disabled = isLastSlide;
    }
}

/**
 * Muestra el indicador de curso completado
 */
function mostrarCompletado() {
    const completadoIndicator = document.getElementById('completado-indicator');
    const btnSiguiente = document.getElementById('btn-siguiente');

    if (completadoIndicator) {
        completadoIndicator.style.display = 'block';
    }

    if (btnSiguiente) {
        btnSiguiente.disabled = true;
    }

    console.log('[CURSOS] ✅ Curso completado!');
}

/**
 * Pinta visualmente el contador y la barra basándose en la variable global
 */
function renderizarProgresoGlobal() {
    const contador = document.getElementById('cursos-completados');
    if (contador) {
        contador.textContent = cursosCompletados;
    }

    const fillBar = document.getElementById('progress-fill-academy');
    if (fillBar && totalCursos > 0) {
        const porcentaje = (cursosCompletados / totalCursos) * 100;
        fillBar.style.width = Math.min(porcentaje, 100) + '%'; // Aseguramos que no pase del 100%
    }
}

/**
 * Guarda el progreso del usuario (diapositiva alcanzada)
 */
async function guardarProgreso(numeroDiapositiva) {
    if (!estadoCurso.id_curso) return;

    try {
        // Recordamos si ANTES de esta petición el curso ya estaba completado
        const estabaCompletadoPreviamente = estadoCurso.progreso ? estadoCurso.progreso.completado : false;

        const response = await window.fetchWithAuth(
            `${API_BASE}/cursos/${estadoCurso.id_curso}/progreso`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ diapositiva_numero: numeroDiapositiva })
            }
        );

        if (response.ok) {
            const progreso = await response.json();
            estadoCurso.progreso = progreso;

            // SOLO sumamos 1 al contador si acaba de ser completado por primera vez ahora mismo
            if (!estabaCompletadoPreviamente && progreso.completado) {
                cursosCompletados += 1;
                renderizarProgresoGlobal();
            }

            console.log(`[PROGRESO] Guardado: diap ${numeroDiapositiva}, completado=${progreso.completado}`);
        } else {
            console.error('[PROGRESO] Error al guardar:', response.status);
        }
    } catch (err) {
        console.error('[PROGRESO] Error de conexión:', err);
    }
}

/**
 * Muestra error en UI
 */
function mostrarErrorCursos(mensaje) {
    const grid = document.getElementById('cursos-grid');
    if (grid) {
        grid.innerHTML = `<div class="error-message">${mensaje}</div>`;
    }
}

// ================================================================
// FUNCIONES DEL CHAT (EXISTENTES)
// ================================================================

/**
 * Envía un mensaje al chatbot y muestra la respuesta
 */
async function enviarMensaje(mensaje, inputElement, chatContainer, sendBtn) {
    // Verificar autenticación
    console.log('[CHAT] Enviando mensaje...');

    if (!mensaje) return;

    // Bloquear input y botón durante la solicitud
    inputElement.disabled = true;
    sendBtn.disabled = true;

    // Guardar placeholder original y mostrar estado de carga
    const placeholderOriginal = inputElement.placeholder;
    inputElement.placeholder = 'Escribiendo...';

    // Mostrar el mensaje del usuario en el chat
    agregarMensajeAlChat(chatContainer, mensaje, 'user');

    // Limpiar el input inmediatamente después de mostrarlo
    inputElement.value = '';

    // Mostrar bubble con puntitos animados
    const loadingBubble = agregarMensajeCargando(chatContainer);

    try {
        const response = await window.fetchWithAuth(`${API_BASE}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: mensaje
            })
        });

        // Remover el bubble de cargando siempre
        loadingBubble.remove();

        const data = await response.json();

        if (!response.ok) {
            // Manejar errores específicos del servidor
            const errorMsg = data.detail || 'Error al procesar el mensaje';
            
            // Si es error de autenticación
            if (response.status === 401) {
                mostrarError(chatContainer, `🔒 ${errorMsg}`);
            }
            // Si es error de límite de caracteres o validación
            else if (response.status === 400) {
                mostrarError(chatContainer, `⚠️ ${errorMsg}`);
            }   
            // Si es error de límite de mensajes (429)
            else if (response.status === 429) {
                mostrarError(chatContainer, `⏱️ ${errorMsg}`);
            }
            // Si es error de servicio no disponible (503) - cuota agotada
            else if (response.status === 503) {
                mostrarError(chatContainer, `🚫 ${errorMsg}`);
            }
            // Si es error del servidor (500)
            else if (response.status === 500) {
                mostrarError(chatContainer, `❌ ${errorMsg}`);
            }
            // Otros errores
            else {
                mostrarError(chatContainer, `❌ Error: ${errorMsg}`);
            }
            return;
        }

        // Mostrar respuesta del modelo
        agregarMensajeAlChat(chatContainer, data.respuesta_ia, 'ai');

    } catch (err) {
        // Remover el bubble de cargando en caso de error de red
        loadingBubble.remove();
        
        console.error('[CHAT] Error de conexión:', err);
        mostrarError(chatContainer, `❌ Error de conexión con el servidor. Verifica que el backend esté ejecutándose en ${API_BASE}`);
    } finally {
        // Restaurar input y botón
        inputElement.disabled = false;
        sendBtn.disabled = false;
        inputElement.placeholder = placeholderOriginal; // Restaurar placeholder original
        inputElement.value = ''; // Limpiar el input después de enviar
        inputElement.focus();
    }
}

/**
 * Agrega un mensaje al contenedor del chat
 */
function agregarMensajeAlChat(chatContainer, mensaje, tipo) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${tipo}`;
    if (tipo === 'ai') {
        bubble.innerHTML = formatearMensajeIA(mensaje);
    } else {
        bubble.textContent = mensaje;
    }
    chatContainer.appendChild(bubble);

    // Scroll hacia el último mensaje
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Agrega un mensaje con puntitos animados para indicar que se está cargando
 */
function agregarMensajeCargando(chatContainer) {
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble ai typing';
    
    // Crear 3 puntitos para la animación
    for (let i = 0; i < 3; i++) {
        const dot = document.createElement('span');
        dot.className = 'typing-dot';
        bubble.appendChild(dot);
    }
    
    chatContainer.appendChild(bubble);

    // Scroll hacia el último mensaje
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    return bubble;
}

/**
 * Muestra un mensaje de error en el chat
 */
function mostrarError(chatContainer, mensaje) {
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble ai error';
    bubble.textContent = mensaje;
    chatContainer.appendChild(bubble);

    // Scroll hacia el último mensaje
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Formatea respuesta del modelo con soporte de negritas en markdown (**texto**)
 * y saltos de linea, escapando HTML para evitar inyecciones.
 */
function formatearMensajeIA(mensaje) {
    const texto = String(mensaje ?? '');
    const escapado = texto
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    return escapado
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
}

// VALIDAR AUTENTICACIÓN CENTRALIZADA
(async () => {
    const result = await window.validateAuthToken();
    if (!result.valid) {
        window.clearAuthSession();
        window.location.replace('login.html');
        return;
    }

    window.setCurrentUserData(result.user);

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAcademiaPage, { once: true });
    } else {
        initAcademiaPage();
    }
})();

/**
 * Formatea el contenido de la diapositiva para asegurar que las imágenes se vean
 */
function formatearContenidoDiapositiva(contenido) {
    if (!contenido) return "";
    
    let texto = contenido.trim();

    // 1. ¿Es simplemente una URL directa de una imagen? (termina en png, jpg, etc)
    const esUrlDeImagen = /^(http|https):\/\/[^ "]+(\.(jpeg|jpg|gif|png|webp|svg))(\?.*)?$/i.test(texto);
    
    // O si es una URL de Supabase (a veces no terminan en .png si tienen parámetros)
    const esUrlSupabase = texto.startsWith('http') && texto.includes('/storage/v1/object/public/');

    if (esUrlDeImagen || esUrlSupabase) {
        // Envolvemos la URL en una etiqueta de imagen bonita
        return `<div style="text-align: center; height: 100%; display: flex; align-items: center; justify-content: center;">
                    <img src="${texto}" alt="Diapositiva" style="max-width: 100%; max-height: 60vh; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.15); object-fit: contain;">
                </div>`;
    }

    // 2. ¿Tiene formato Markdown de imágenes? ej: ![Mi imagen](https://...)
    let html = texto.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, 
        '<img src="$2" alt="$1" style="max-width: 100%; border-radius: 8px; margin: 15px 0;">');

    // 3. Convertir saltos de línea normales en saltos de línea HTML (<br>)
    // (Solo si no empieza con etiquetas HTML para no romper código HTML que metas manualmente)
    if (!html.startsWith('<')) {
        html = html.replace(/\n/g, '<br>');
    }

    return html;
}