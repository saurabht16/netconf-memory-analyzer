"""
NETCONF Client for Memory Leak Testing
Executes NETCONF RPC operations to trigger memory usage in target processes
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import time
import logging
import socket
import threading

from .device_connector import DeviceConnector

@dataclass
class NetconfConfig:
    """Configuration for NETCONF operations"""
    host: str
    port: int = 830
    username: str = ""
    password: str = ""
    timeout: int = 30
    capabilities: List[str] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = [
                "urn:ietf:params:netconf:base:1.0",
                "urn:ietf:params:netconf:capability:startup:1.0",
                "urn:ietf:params:netconf:capability:candidate:1.0"
            ]

@dataclass
class RpcOperation:
    """NETCONF RPC operation definition"""
    name: str
    xml_content: str
    description: str = ""
    expected_response: str = "ok"
    timeout: int = 30
    repeat_count: int = 1
    delay_between_repeats: float = 0.0

class NetconfClient:
    """NETCONF client for executing RPC operations"""
    
    def __init__(self, config: NetconfConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session_id = None
        self.message_id = 1
        self.connected = False
        self.socket = None
        
    def connect(self) -> bool:
        """Connect to NETCONF server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.timeout)
            self.socket.connect((self.config.host, self.config.port))
            
            # Send hello message
            hello_msg = self._build_hello_message()
            self._send_message(hello_msg)
            
            # Receive server hello
            response = self._receive_message()
            if self._parse_hello_response(response):
                self.connected = True
                self.logger.info(f"Connected to NETCONF server {self.config.host}:{self.config.port}")
                return True
            else:
                self.logger.error("Failed to establish NETCONF session")
                return False
                
        except Exception as e:
            self.logger.error(f"NETCONF connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from NETCONF server"""
        if self.connected and self.socket:
            try:
                # Send close session
                close_msg = self._build_close_session()
                self._send_message(close_msg)
                self.socket.close()
            except Exception:
                pass
            finally:
                self.connected = False
                self.socket = None
                self.logger.info("Disconnected from NETCONF server")
    
    def execute_rpc(self, operation: RpcOperation) -> List[Dict[str, Any]]:
        """Execute a single RPC operation"""
        if not self.connected:
            raise ConnectionError("Not connected to NETCONF server")
        
        results = []
        
        for i in range(operation.repeat_count):
            try:
                start_time = time.time()
                
                # Build and send RPC
                rpc_msg = self._build_rpc_message(operation.xml_content)
                self._send_message(rpc_msg)
                
                # Receive response
                response = self._receive_message()
                end_time = time.time()
                
                # Parse response
                result = {
                    "operation": operation.name,
                    "iteration": i + 1,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": end_time - start_time,
                    "response": response,
                    "status": "success" if self._is_success_response(response) else "error",
                    "message_id": self.message_id - 1
                }
                
                results.append(result)
                self.logger.info(f"RPC '{operation.name}' iteration {i+1} completed in {result['duration']:.3f}s")
                
                # Delay between repeats
                if i < operation.repeat_count - 1 and operation.delay_between_repeats > 0:
                    time.sleep(operation.delay_between_repeats)
                    
            except Exception as e:
                result = {
                    "operation": operation.name,
                    "iteration": i + 1,
                    "start_time": time.time(),
                    "end_time": time.time(),
                    "duration": 0,
                    "response": "",
                    "status": "error",
                    "error": str(e),
                    "message_id": self.message_id
                }
                results.append(result)
                self.logger.error(f"RPC '{operation.name}' iteration {i+1} failed: {e}")
        
        return results
    
    def execute_rpc_sequence(self, operations: List[RpcOperation]) -> Dict[str, List[Dict[str, Any]]]:
        """Execute a sequence of RPC operations"""
        if not self.connected:
            raise ConnectionError("Not connected to NETCONF server")
        
        all_results = {}
        
        for operation in operations:
            self.logger.info(f"Executing RPC operation: {operation.name}")
            results = self.execute_rpc(operation)
            all_results[operation.name] = results
        
        return all_results
    
    def load_rpc_from_file(self, file_path: Path) -> RpcOperation:
        """Load RPC operation from XML file"""
        try:
            with open(file_path, 'r') as f:
                xml_content = f.read()
            
            # Try to extract operation name from XML or use filename
            try:
                root = ET.fromstring(xml_content)
                operation_name = root.tag
            except:
                operation_name = file_path.stem
            
            return RpcOperation(
                name=operation_name,
                xml_content=xml_content,
                description=f"Loaded from {file_path}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load RPC from {file_path}: {e}")
            raise
    
    def load_rpc_directory(self, directory_path: Path) -> List[RpcOperation]:
        """Load all RPC operations from a directory"""
        operations = []
        
        if not directory_path.exists():
            self.logger.error(f"Directory {directory_path} does not exist")
            return operations
        
        for xml_file in directory_path.glob("*.xml"):
            try:
                operation = self.load_rpc_from_file(xml_file)
                operations.append(operation)
                self.logger.info(f"Loaded RPC operation: {operation.name}")
            except Exception as e:
                self.logger.error(f"Failed to load {xml_file}: {e}")
        
        return operations
    
    def _build_hello_message(self) -> str:
        """Build NETCONF hello message"""
        capabilities = ""
        for cap in self.config.capabilities:
            capabilities += f"<capability>{cap}</capability>\n"
        
        hello = f"""<?xml version="1.0" encoding="UTF-8"?>
<hello xmlns="urn:ietf:params:netconf:base:1.0">
<capabilities>
{capabilities}
</capabilities>
</hello>
]]>]]>"""
        return hello
    
    def _build_rpc_message(self, rpc_content: str) -> str:
        """Build NETCONF RPC message"""
        # Remove XML declaration if present
        if rpc_content.startswith('<?xml'):
            rpc_content = '\n'.join(rpc_content.split('\n')[1:])
        
        rpc = f"""<?xml version="1.0" encoding="UTF-8"?>
<rpc message-id="{self.message_id}" xmlns="urn:ietf:params:netconf:base:1.0">
{rpc_content}
</rpc>
]]>]]>"""
        
        self.message_id += 1
        return rpc
    
    def _build_close_session(self) -> str:
        """Build close session message"""
        close = f"""<?xml version="1.0" encoding="UTF-8"?>
<rpc message-id="{self.message_id}" xmlns="urn:ietf:params:netconf:base:1.0">
<close-session/>
</rpc>
]]>]]>"""
        
        self.message_id += 1
        return close
    
    def _send_message(self, message: str):
        """Send message to NETCONF server"""
        if self.socket:
            self.socket.send(message.encode('utf-8'))
    
    def _receive_message(self) -> str:
        """Receive message from NETCONF server"""
        if not self.socket:
            return ""
        
        data = b""
        while True:
            chunk = self.socket.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"]]>]]>" in data:
                break
        
        return data.decode('utf-8').replace("]]>]]>", "")
    
    def _parse_hello_response(self, response: str) -> bool:
        """Parse hello response from server"""
        try:
            # Simple check for hello response
            return "<hello" in response and "<capabilities>" in response
        except Exception:
            return False
    
    def _is_success_response(self, response: str) -> bool:
        """Check if RPC response indicates success"""
        try:
            # Simple success check - no rpc-error elements
            return "<rpc-error>" not in response and ("<ok/>" in response or "<data>" in response)
        except Exception:
            return False
    
    def __enter__(self):
        """Context manager entry"""
        if not self.connect():
            raise ConnectionError("Failed to connect to NETCONF server")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect() 