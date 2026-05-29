import socket
import threading
import rsa
import datetime
from cryptography.fernet import Fernet
from gui import ChatGUI
import gui

# RSA keys
client_public_key, client_private_key = rsa.newkeys(1024)
server_public_key = None
fernet = None

IP = "127.0.0.1"
PORT = 5000

username = input("Choose a username: ")
# this is why it says "you" and doesn't repeat my name 2x
gui.set_local_username(username)

def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def receive_messages(sock):
    global server_public_key, fernet
    #Receive server public key
    key_data = sock.recv(4096)
    if not key_data:
        print("Connection closed.")
        return
    server_public_key = rsa.PublicKey.load_pkcs1(key_data)
    print("Received server's public key.")

    #Send client public key
    sock.send(client_public_key.save_pkcs1())

    #Generate AES key and send it encrypted with server's RSA key
    aes_key = Fernet.generate_key()
    fernet = Fernet(aes_key)
    enc_aes_key = rsa.encrypt(aes_key, server_public_key)
    length = len(enc_aes_key).to_bytes(4, "big")
    sock.send(length + enc_aes_key)

    #receive AES-encrypted messages from server
    while True:
        len_bytes = recv_exact(sock, 4)
        if not len_bytes:
            print("Connection closed.")
            break

        msg_len = int.from_bytes(len_bytes, "big")
        encrypted_msg = recv_exact(sock, msg_len)
        if not encrypted_msg:
            print("Connection closed.")
            break

        try:
            decrypted = fernet.decrypt(encrypted_msg).decode()
            gui.display_message(decrypted)
        except Exception:
            print("Failed to decrypt message.")
            break

def send_encrypted(sock, msg):
    global fernet, username
    while fernet is None:
        time.sleep(0.1)

    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    full_msg = f"[{timestamp}] {username}: {msg}"

    ciphertext = fernet.encrypt(full_msg.encode())
    length_key = len(ciphertext).to_bytes(4, "big")
    sock.send(length_key + ciphertext)

    # return the formatted message so the GUI can display it
    return full_msg


def start_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((IP, PORT))

    threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()

    #wait until AES key is set by receive_messages
    while fernet is None:
        time.sleep(0.1)

    chat = ChatGUI(send_callback=lambda msg: send_encrypted(sock, msg))
    chat.run()

if __name__ == "__main__":
    start_client()
