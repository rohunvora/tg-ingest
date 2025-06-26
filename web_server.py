#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tg_export.quick_export import create_app

if __name__ == '__main__':
    app = create_app()
    
    # Try different ports if 5000 is in use
    ports = [8080, 5001, 5000, 8000]
    server_started = False
    
    for port in ports:
        try:
            print(f"\n🚀 Starting Quick Export server...")
            print(f"📱 Open your browser to: http://127.0.0.1:{port}\n")
            print("Press Ctrl+C to stop the server\n")
            app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
            server_started = True
            break
        except OSError as e:
            if "Address already in use" in str(e):
                continue
            else:
                raise
        except KeyboardInterrupt:
            print("\n\n✅ Server stopped")
            break
    
    if not server_started:
        print("\n❌ Could not find an available port")
        print("Try running with a specific port:")
        print("  PORT=8888 python web_server.py")