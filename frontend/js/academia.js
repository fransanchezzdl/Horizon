document.addEventListener('DOMContentLoaded', () => {
    const chatAsesor = document.getElementById('chatAsesor');
    const chatHeader = chatAsesor.querySelector('.advisor-header');
    const sendBtn = document.getElementById('sendMsg');
    const chatInput = chatAsesor.querySelector('input');

    // Función para minimizar / maximizar
    if (chatHeader) {
        chatHeader.addEventListener('click', () => {
            chatAsesor.classList.toggle('collapsed');
        });
    }

    // Simulación de envío
    if (sendBtn && chatInput) {
        sendBtn.addEventListener('click', () => {
            if (chatInput.value.trim() !== "") {
                console.log("Mensaje enviado:", chatInput.value);
                chatInput.value = "";
            }
        });
    }
});