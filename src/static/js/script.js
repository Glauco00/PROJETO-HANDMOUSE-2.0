// script.js

document.addEventListener('DOMContentLoaded', function () {
    const startButton = document.getElementById('start-button');
    const stopButton = document.getElementById('stop-button');
    const statusLed = document.getElementById('status-led');
    const statusText = document.getElementById('status-text');
    const cameraFeed = document.getElementById('camera-feed');

    // Inicializa o Socket.IO
    const socket = io();

    // Função para atualizar o status
    function updateStatus(isActive) {
        if (isActive) {
            statusText.textContent = 'Ativado';
            statusText.style.color = 'green';
            statusLed.style.backgroundColor = 'green';
        } else {
            statusText.textContent = 'Desativado';
            statusText.style.color = 'red';
            statusLed.style.backgroundColor = 'red';
        }
    }

    // Define o estado inicial como desativado
    updateStatus(false);

    // Envia o comando para ativar o controle do HandMouse
    startButton.addEventListener('click', function () {
        socket.emit('start_handmouse'); // Envia o evento para o servidor
        updateStatus(true); // Atualiza o status para ativado
    });

    // Envia o comando para parar o controle do HandMouse
    stopButton.addEventListener('click', function () {
        socket.emit('stop_handmouse'); // Envia o evento para o servidor
        updateStatus(false); // Atualiza o status para desativado
    });

    // Recebe os frames da câmera e atualiza o feed
    socket.on('camera_frame', function (data) {
        cameraFeed.src = `data:image/jpeg;base64,${data.frame}`;
    });

    // Inicia automaticamente a exibição da câmera ao carregar a página
    socket.emit('start_capture');
});

