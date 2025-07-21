#!/usr/bin/env python3
"""
Create Sample RPC Files for NETCONF Testing
"""

import sys
from pathlib import Path

def create_sample_rpcs(output_dir):
    """Create sample RPC files for testing"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    sample_rpcs = {
        "get_config.xml": """<?xml version="1.0" encoding="UTF-8"?>
<get-config>
    <source>
        <running/>
    </source>
</get-config>""",
        
        "get_state.xml": """<?xml version="1.0" encoding="UTF-8"?>
<get>
    <filter type="subtree">
        <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
            <interface>
                <name/>
                <oper-status/>
            </interface>
        </interfaces>
    </filter>
</get>""",
        
        "edit_config.xml": """<?xml version="1.0" encoding="UTF-8"?>
<edit-config>
    <target>
        <candidate/>
    </target>
    <config>
        <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
            <interface>
                <name>test-interface</name>
                <description>Memory leak test interface</description>
                <enabled>true</enabled>
            </interface>
        </interfaces>
    </config>
</edit-config>""",
        
        "lock_unlock.xml": """<?xml version="1.0" encoding="UTF-8"?>
<lock>
    <target>
        <candidate/>
    </target>
</lock>""",

        "get_capabilities.xml": """<?xml version="1.0" encoding="UTF-8"?>
<get>
    <filter type="xpath" select="/netconf-state/capabilities"/>
</get>""",

        "commit.xml": """<?xml version="1.0" encoding="UTF-8"?>
<commit/>""",

        "discard_changes.xml": """<?xml version="1.0" encoding="UTF-8"?>
<discard-changes/>"""
    }
    
    for filename, content in sample_rpcs.items():
        file_path = output_dir / filename
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Created: {file_path}")
    
    print(f"\n✅ Created {len(sample_rpcs)} sample RPC files in {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_sample_rpcs.py <output_directory>")
        sys.exit(1)
    
    create_sample_rpcs(sys.argv[1]) 