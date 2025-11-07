const socket = io();

socket.on('receive_message', (data) => {
  const messagesDiv = document.getElementById('messages');
  const msg = document.createElement('div');
  msg.textContent = `Encrypted: ${data.encrypted}`;
  messagesDiv.appendChild(msg);
});

function sendMessage() {
  const input = document.getElementById('msgBox');
  const message = input.value;
  socket.emit('send_message', { message });
  input.value = '';
}
