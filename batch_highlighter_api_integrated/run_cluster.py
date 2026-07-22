#!/usr/bin/env python
"""
Cluster manager for running multiple API instances with a built-in load balancer.

This script:
1. Launches multiple Uvicorn worker instances on different ports
2. Runs a simple round-robin load balancer in front of them
3. Supports graceful shutdown of all instances
"""
import asyncio
import aiohttp
import aiohttp.web
import signal
import socket
import subprocess
import sys
import os
from typing import List
from concurrent.futures import ThreadPoolExecutor

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.settings import get_settings


class LoadBalancer:
    """Simple round-robin load balancer for multiple API instances."""
    
    def __init__(self, hosts: List[str]):
        self.hosts = hosts
        self.current_index = 0
        self.lock = asyncio.Lock()
    
    async def handle_request(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Route request to the next available host using round-robin."""
        async with self.lock:
            host = self.hosts[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.hosts)
        
        try:
            # Forward the request to the target host
            async with aiohttp.ClientSession() as session:
                url = f"http://{host}/{request.path.lstrip('/')}"
                method = request.method
                
                # Copy headers (except host)
                headers = {k: v for k, v in request.headers.items() if k.lower() != 'host'}
                
                # Forward request body if present
                body = await request.read() if request.can_read_body else None
                
                async with session.request(method, url, headers=headers, data=body,
                                          allow_redirects=False) as resp:
                    # Build response
                    response = aiohttp.web.Response(
                        status=resp.status,
                        headers={k: v for k, v in resp.headers.items() if k.lower() != 'transfer-encoding'}
                    )
                    response.body = await resp.read()
                    return response
        except Exception as e:
            return aiohttp.web.Response(status=502, text=f"Bad Gateway: {str(e)}")


class ClusterManager:
    """Manages multiple API instances and the load balancer."""
    
    def __init__(self):
        self.settings = get_settings()
        self.processes: List[subprocess.Popen] = []
        self.load_balancer: LoadBalancer | None = None
        self.app: aiohttp.web.Application | None = None
    
    def get_available_ports(self, count: int, start_port: int = None) -> List[int]:
        """Get a list of available ports for worker instances."""
        if start_port is None:
            start_port = self.settings.port + 1
        
        ports = []
        port = start_port
        while len(ports) < count:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                try:
                    sock.bind(('', port))
                    ports.append(port)
                except OSError:
                    port += 1
                finally:
                    port += 1
        return ports
    
    def start_worker(self, port: int) -> subprocess.Popen:
        """Start a single worker instance on the specified port."""
        env = os.environ.copy()
        env['PORT'] = str(port)
        env['HOST'] = '127.0.0.1'
        env['WORKERS'] = '1'  # Each process handles one worker
        env['ENVIRONMENT'] = 'production'
        
        cmd = [
            sys.executable, '-m', 'uvicorn',
            'main:app',
            '--host', '127.0.0.1',
            '--port', str(port),
            '--workers', '1',
            '--no-reload',
            '--access-log'
        ]
        
        print(f"[Worker-{port}] Starting on port {port}...")
        
        process = subprocess.Popen(
            cmd,
            env=env,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        return process
    
    async def run_load_balancer(self, hosts: List[str], lb_port: int):
        """Run the load balancer."""
        self.load_balancer = LoadBalancer(hosts)
        self.app = aiohttp.web.Application()
        self.app.router.add_route('*', '/{path:.*}', self.load_balancer.handle_request)
        
        runner = aiohttp.web.AppRunner(self.app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, '0.0.0.0', lb_port)
        await site.start()
        
        print(f"[Load Balancer] Running on http://0.0.0.0:{lb_port}")
        print(f"[Load Balancer] Proxying to: {', '.join(hosts)}")
        
        return runner
    
    def shutdown(self):
        """Gracefully shutdown all workers and the load balancer."""
        print("\n[Cluster] Shutting down...")
        for process in self.processes:
            print(f"[Cluster] Stopping worker process (PID: {process.pid})...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("[Cluster] All workers stopped.")
    
    async def run(self, worker_count: int = None):
        """Start the cluster with load balancer and workers."""
        if worker_count is None:
            worker_count = self.settings.workers
        
        # Use a ThreadPoolExecutor for blocking operations
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            # Get available ports for workers
            ports = await loop.run_in_executor(executor, self.get_available_ports, worker_count)
        
        # Start workers
        for port in ports:
            process = self.start_worker(port)
            self.processes.append(process)
        
        # Give workers time to start
        await asyncio.sleep(2)
        
        # Create host list for workers
        hosts = [f"127.0.0.1:{port}" for port in ports]
        
        # Start load balancer
        lb_port = self.settings.port
        runner = await self.run_load_balancer(hosts, lb_port)
        
        print(f"\n[Cluster] {'='*50}")
        print(f"[Cluster] API Cluster is running!")
        print(f"[Cluster] Main endpoint: http://0.0.0.0:{lb_port}")
        print(f"[Cluster] Worker instances: {len(hosts)}")
        print(f"[Cluster] {'='*50}\n")
        
        # Handle shutdown signals
        def signal_handler(sig, frame):
            print(f"\n[Cluster] Received signal {sig}")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
                # Check if any workers have died
                for i, process in enumerate(self.processes):
                    if process.poll() is not None:
                        print(f"[Cluster] Worker {ports[i]} died, restarting...")
                        new_process = self.start_worker(ports[i])
                        self.processes[i] = new_process
                        hosts[i] = f"127.0.0.1:{ports[i]}"
                        self.load_balancer.hosts = hosts
        except asyncio.CancelledError:
            pass
        finally:
            await runner.cleanup()
            self.shutdown()


async def main():
    """Main entry point."""
    settings = get_settings()
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    Batch Highlighter API                       ║
║                    Cluster Mode Launcher                        ║
╠═══════════════════════════════════════════════════════════════╣
║  This script starts multiple API instances behind a load      ║
║  balancer for improved performance and fault tolerance.       ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    print(f"[Config] Workers: {settings.workers}")
    print(f"[Config] Base Port: {settings.port}")
    print(f"[Config] Environment: {settings.environment}\n")
    
    manager = ClusterManager()
    await manager.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Cluster] Interrupted by user.")
    except Exception as e:
        print(f"[Cluster] Error: {e}")
        sys.exit(1)
