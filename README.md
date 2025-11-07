🔒 Secure Chat App with End-to-End Encryption

A modern, privacy-focused real-time chat application built with Flask and Socket.IO, featuring end-to-end encryption (E2EE) to keep conversations completely private.

🚀 Features

💬 Real-time chat using Flask-SocketIO

🔐 End-to-End Encryption (AES / RSA) for secure message transfer

🧑‍🤝‍🧑 Multiple users can chat simultaneously

💻 Responsive and modern chat UI

📁 Messages are not stored on the server (privacy-first design)

⚡ Lightweight and easy to deploy

🧩 Tech Stack
Component	Technology
Backend	Flask (Python)
Frontend	HTML, CSS, JavaScript
Real-time Communication	Flask-SocketIO
Encryption	PyCryptodome

🧠 How Encryption Works

Each message is encrypted using a unique symmetric key (AES).

The AES key is then encrypted using RSA public keys before being sent.

The server never has access to the decrypted message or keys — ensuring true end-to-end security.

🧑‍💻 Future Enhancements

📱 Mobile-friendly PWA version

🕵️‍♂️ Anonymous chat mode

🗝️ QR code–based key sharing

🔔 Notifications for new messages
