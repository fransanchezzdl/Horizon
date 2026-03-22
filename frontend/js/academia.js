const API_BASE = window.API_BASE;

// VALIDAR AUTENTICACIÓN CENTRALIZADA
(async () => {
    const result = await window.validateAuthToken();
    if (!result.valid) {
        window.clearAuthSession();
        window.location.replace('login.html');
        return;
    }
})();

document.addEventListener('DOMContentLoaded', () => {
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
});

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