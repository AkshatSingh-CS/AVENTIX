import os
import socket
import subprocess
import sys

def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def main():
    ip = get_lan_ip()
    port = '8000'
    url = f"http://{ip}:{port}"
    
    print("\n" + "="*50)
    print(f"🚀 AVENTIX Development Server (LAN Mode)")
    print("="*50)
    print(f"\nYour app will be accessible on your local network at:\n\n    {url}\n")
    
    try:
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.make(fit=True)
        print("Scan this QR code with your phone/tablet:")
        qr.print_ascii()
    except ImportError:
        print("💡 Tip: Install 'qrcode' (pip install qrcode) to see a scanable QR code here.")
        
    print("\nStarting Django server...")
    print("Make sure your firewall allows inbound connections on port 8000!")
    print("="*50 + "\n")
    
    # Run the server
    subprocess.run([sys.executable, "manage.py", "runserver", f"0.0.0.0:{port}"])

if __name__ == '__main__':
    main()
