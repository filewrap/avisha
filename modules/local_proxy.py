"""Local SOCKS5 proxy that forwards to an upstream authenticated SOCKS5 proxy."""
import socket, threading, struct, socks

def handle_client(client_sock, remote_host, remote_port, remote_user, remote_pw):
    try:
        # SOCKS5 greeting — client sends supported auth methods
        header = client_sock.recv(2)
        if len(header) < 2:
            client_sock.close()
            return
        nmethods = header[1]
        client_sock.recv(nmethods)  # consume method list

        # Reply: no auth required to our local proxy
        client_sock.sendall(b'\x05\x00')

        # SOCKS5 connect request
        data = client_sock.recv(256)
        if len(data) < 4:
            client_sock.close()
            return
        version, cmd, _, atyp = data[0], data[1], data[2], data[3]
        if version != 5 or cmd != 1:
            client_sock.sendall(b'\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00')
            client_sock.close()
            return

        offset = 4
        if atyp == 1:  # IPv4
            addr = socket.inet_ntoa(data[offset:offset+4])
            offset += 4
        elif atyp == 3:  # Domain
            dlen = data[offset]
            offset += 1
            addr = data[offset:offset+dlen].decode()
            offset += dlen
        elif atyp == 4:  # IPv6
            addr = socket.inet_ntop(socket.AF_INET6, data[offset:offset+16])
            offset += 16
        else:
            client_sock.close()
            return

        port = struct.unpack('!H', data[offset:offset+2])[0]

        # Connect through upstream SOCKS5 proxy with auth
        remote = socks.socksocket()
        remote.set_proxy(socks.SOCKS5, remote_host, remote_port,
                         rdns=True, username=remote_user, password=remote_pw)
        remote.settimeout(15)
        remote.connect((addr, port))

        # Send success reply
        reply = b'\x05\x00\x00\x01' + b'\x00' * 6
        client_sock.sendall(reply)

        # Bidirectional forwarding
        def forward(src, dst):
            try:
                while True:
                    d = src.recv(4096)
                    if not d:
                        break
                    dst.sendall(d)
            except:
                pass
            try:
                src.close()
            except:
                pass

        t1 = threading.Thread(target=forward, args=(client_sock, remote), daemon=True)
        t2 = threading.Thread(target=forward, args=(remote, client_sock), daemon=True)
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)
    except Exception as e:
        try:
            client_sock.close()
        except:
            pass


def start_local_proxy(remote_host, remote_port, remote_user, remote_pw, local_port=0):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', local_port))
    srv.listen(50)
    actual_port = srv.getsockname()[1]

    def accept_loop():
        while True:
            try:
                client, _ = srv.accept()
                threading.Thread(
                    target=handle_client,
                    args=(client, remote_host, remote_port, remote_user, remote_pw),
                    daemon=True,
                ).start()
            except:
                break

    t = threading.Thread(target=accept_loop, daemon=True)
    t.start()
    return srv, actual_port
