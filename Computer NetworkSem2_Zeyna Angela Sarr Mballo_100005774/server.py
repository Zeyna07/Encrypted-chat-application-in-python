import socket
import threading
import rsa
from cryptography.fernet import Fernet


server_public_key, server_private_key = rsa.newkeys(1024)

IP = "10.0.102.96"  
PORT = 5000

clients = {}

def recv_exact(sock: socket.socket, n: int) -> bytes | None:
    """Read exactly n bytes from the socket, or return None if closed."""
    data = b""
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def handle_client(client: socket.socket):
    """Read AES-encrypted messages from client, decrypt with client's Fernet,
    then re-encrypt with each recipient's Fernet and forward."""
    while True:
        len_bytes = recv_exact(client, 4)
        if not len_bytes:
            break

        msg_len = int.from_bytes(len_bytes, "big")
        ciphertext = recv_exact(client, msg_len)
        if not ciphertext:
            break

        try:
            plaintext = clients[client]["fernet"].decrypt(ciphertext)
        except Exception:
            print("Server failed to decrypt from client.")
            break

        # Re-encrypt with each recipient's AES (their Fernet) and send
        for other_sock, info in list(clients.items()):
            if other_sock is client:
                continue
            try:
                enc_for_other = info["fernet"].encrypt(plaintext)
                length = len(enc_for_other).to_bytes(4, "big")
                other_sock.send(length + enc_for_other)
            except Exception:
                other_sock.close()
                del clients[other_sock]

    if client in clients:
        del clients[client]
    client.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((IP, PORT))
    server.listen()
    print(f"Server listening on {IP}:{PORT}")

    while True:
        client, addr = server.accept()
        print(f"A new connection was established from {addr}")

        # Send server public key, receive client's public key and client's AES key
        client.send(server_public_key.save_pkcs1())
        client_public_key = rsa.PublicKey.load_pkcs1(client.recv(4096))
        len_bytes = recv_exact(client, 4)
        if not len_bytes:
            client.close()
            continue
        key_len = int.from_bytes(len_bytes, "big")
        enc_aes_key = recv_exact(client, key_len)
        if not enc_aes_key:
            client.close()
            continue

        try:
            aes_key = rsa.decrypt(enc_aes_key, server_private_key)
        except Exception:
            client.close()
            continue

        fernet = Fernet(aes_key)
        clients[client] = {"public_key": client_public_key, "fernet": fernet}

        threading.Thread(target=handle_client, args=(client,), daemon=True).start()

if __name__ == "__main__":
    start_server()
