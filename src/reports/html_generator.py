"""
HTML report generator for memory leak analysis
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import json

from ..models.leak_data import LeakDatabase, MemoryLeak, LeakType


class HTMLGenerator:
    """Generate HTML reports from memory leak data"""
    
    def __init__(self):
        self.template = self._get_html_template()
    
    def generate_report(self, leak_db: LeakDatabase, output_path: Path):
        """Generate a comprehensive HTML report"""
        stats = leak_db.get_statistics()
        leaks = leak_db.get_all_leaks()
        
        # Prepare data for template
        charts_data = self._prepare_charts_data(stats)
        leaks_json = json.dumps(self._prepare_leaks_data(leaks))
        
        # Generate HTML content with proper substitutions
        html_content = self.template
        html_content = html_content.replace('{title}', 'Memory Leak Analysis Report')
        html_content = html_content.replace('{generation_time}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        html_content = html_content.replace('{total_leaks}', str(stats['total_leaks']))
        html_content = html_content.replace('{total_bytes}', f"{stats['total_bytes']:,}")
        html_content = html_content.replace('{high_severity}', str(stats['by_severity']['HIGH']))
        html_content = html_content.replace('{medium_severity}', str(stats['by_severity']['MEDIUM']))
        html_content = html_content.replace('{severity_data}', charts_data['severity_data'])
        html_content = html_content.replace('{type_data}', charts_data['type_data'])
        html_content = html_content.replace('{leaks_data}', leaks_json)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _prepare_leaks_data(self, leaks: List[MemoryLeak]) -> List[Dict[str, Any]]:
        """Prepare leak data for HTML template"""
        leaks_data = []
        
        for i, leak in enumerate(leaks):
            leak_data = {
                'id': i,
                'type': leak.leak_type.value.replace('_', ' ').title(),
                'severity': leak.get_severity(),
                'size': leak.size,
                'size_formatted': f"{leak.size:,}",
                'count': leak.count,
                'location': leak.primary_location,
                'message': leak.message,
                'stack_trace': [str(frame) for frame in leak.stack_trace],
                'severity_class': leak.get_severity().lower()
            }
            leaks_data.append(leak_data)
        
        return leaks_data
    
    def _prepare_charts_data(self, stats: Dict[str, Any]) -> Dict[str, str]:
        """Prepare data for JavaScript charts"""
        # Severity chart data
        severity_data = []
        for severity, count in stats['by_severity'].items():
            if count > 0:
                severity_data.append({'label': severity, 'value': count})
        
        # Type chart data
        type_data = []
        for leak_type, info in stats['by_type'].items():
            if info['count'] > 0:
                type_data.append({
                    'label': leak_type.replace('_', ' ').title(),
                    'value': info['count'],
                    'bytes': info['bytes']
                })
        
        return {
            'severity_data': json.dumps(severity_data),
            'type_data': json.dumps(type_data)
        }
    
    def _get_html_template(self) -> str:
        """Get the HTML template for the report"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }

        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }

        .stat-label {
            font-size: 1.1em;
            color: #666;
        }

        .charts-section {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }

        .charts-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }

        .chart-container {
            position: relative;
            height: 300px;
        }

        .leaks-section {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .section-title {
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }

        .leak-item {
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-bottom: 20px;
            overflow: hidden;
        }

        .leak-header {
            padding: 15px 20px;
            background: #f8f9fa;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background-color 0.3s;
        }

        .leak-header:hover {
            background: #e9ecef;
        }

        .leak-title {
            font-weight: bold;
            color: #333;
        }

        .severity-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }

        .severity-badge.high {
            background-color: #dc3545;
            color: white;
        }

        .severity-badge.medium {
            background-color: #ffc107;
            color: #212529;
        }

        .severity-badge.low {
            background-color: #28a745;
            color: white;
        }

        .leak-details {
            padding: 20px;
            background: white;
            display: none;
        }

        .leak-details.active {
            display: block;
        }

        .detail-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }

        .detail-item {
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }

        .detail-label {
            font-weight: bold;
            color: #666;
            margin-bottom: 5px;
        }

        .detail-value {
            color: #333;
        }

        .stack-trace {
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            overflow-x: auto;
        }

        .stack-frame {
            padding: 2px 0;
        }

        .toggle-icon {
            font-size: 1.2em;
            transition: transform 0.3s;
        }

        .toggle-icon.rotated {
            transform: rotate(180deg);
        }

        .filter-controls {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
        }

        .filter-row {
            display: grid;
            grid-template-columns: 2fr 1.5fr 1.5fr 1fr auto;
            gap: 15px;
            align-items: end;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .filter-group label {
            font-weight: bold;
            color: #555;
            font-size: 0.9em;
        }

        .filter-group input,
        .filter-group select {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }

        .filter-group input:focus,
        .filter-group select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
        }

        .filter-controls button {
            padding: 8px 16px;
            background-color: #667eea;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            height: fit-content;
        }

        .filter-controls button:hover {
            background-color: #5a6fd8;
        }

        .leak-item.hidden {
            display: none !important;
        }

        @media (max-width: 768px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }

            .detail-grid {
                grid-template-columns: 1fr;
            }

            .container {
                padding: 10px;
            }

            .filter-row {
                grid-template-columns: 1fr;
                gap: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>Generated on {generation_time}</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_leaks}</div>
                <div class="stat-label">Total Issues</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_bytes}</div>
                <div class="stat-label">Bytes Affected</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{high_severity}</div>
                <div class="stat-label">High Severity</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{medium_severity}</div>
                <div class="stat-label">Medium Severity</div>
            </div>
        </div>

        <div class="charts-section">
            <h2 class="section-title">Analysis Charts</h2>
            <div class="charts-grid">
                <div>
                    <h3 style="text-align: center; margin-bottom: 15px;">Issues by Severity</h3>
                    <div class="chart-container">
                        <canvas id="severityChart"></canvas>
                    </div>
                </div>
                <div>
                    <h3 style="text-align: center; margin-bottom: 15px;">Issues by Type</h3>
                    <div class="chart-container">
                        <canvas id="typeChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <div class="leaks-section">
            <h2 class="section-title">Detailed Issues (<span id="visible-count">{total_leaks}</span> of <span id="total-count">{total_leaks}</span> shown)</h2>
            
            <!-- Filter Controls -->
            <div class="filter-controls">
                <div class="filter-row">
                    <div class="filter-group">
                        <label for="search-input">Search:</label>
                        <input type="text" id="search-input" placeholder="Search in any field..." />
                    </div>
                    <div class="filter-group">
                        <label for="file-filter">File:</label>
                        <input type="text" id="file-filter" placeholder="Filter by file..." />
                    </div>
                    <div class="filter-group">
                        <label for="function-filter">Function:</label>
                        <input type="text" id="function-filter" placeholder="Filter by function..." />
                    </div>
                    <div class="filter-group">
                        <label for="severity-filter">Severity:</label>
                        <select id="severity-filter">
                            <option value="">All</option>
                            <option value="HIGH">High</option>
                            <option value="MEDIUM">Medium</option>
                            <option value="LOW">Low</option>
                        </select>
                    </div>
                    <button onclick="clearFilters()">Clear Filters</button>
                </div>
            </div>
            
            <div id="leaks-container">
                <!-- Leaks will be inserted here by JavaScript -->
            </div>
        </div>
    </div>

    <script>
        // Chart data
        const severityData = {severity_data};
        const typeData = {type_data};

        // Severity Chart
        const severityCtx = document.getElementById('severityChart').getContext('2d');
        new Chart(severityCtx, {
            type: 'doughnut',
            data: {
                labels: severityData.map(item => item.label),
                datasets: [{
                    data: severityData.map(item => item.value),
                    backgroundColor: [
                        '#dc3545',  // High
                        '#ffc107',  // Medium
                        '#28a745'   // Low
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        // Type Chart
        const typeCtx = document.getElementById('typeChart').getContext('2d');
        new Chart(typeCtx, {
            type: 'bar',
            data: {
                labels: typeData.map(item => item.label),
                datasets: [{
                    label: 'Issues',
                    data: typeData.map(item => item.value),
                    backgroundColor: '#667eea'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Leaks data
        const leaks = {leaks_data};

        // Generate leaks HTML
        function generateLeaksHTML() {
            const container = document.getElementById('leaks-container');
            
            leaks.forEach((leak, index) => {
                const leakDiv = document.createElement('div');
                leakDiv.className = 'leak-item';
                leakDiv.innerHTML = `
                    <div class="leak-header" onclick="toggleLeak(${index})">
                        <div class="leak-title">
                            ${leak.type} - ${leak.location.substring(0, 80)}${leak.location.length > 80 ? '...' : ''}
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span class="severity-badge ${leak.severity_class}">${leak.severity}</span>
                            <span>${leak.size_formatted} bytes</span>
                            <span class="toggle-icon" id="icon-${index}">▼</span>
                        </div>
                    </div>
                    <div class="leak-details" id="details-${index}">
                        <div class="detail-grid">
                            <div class="detail-item">
                                <div class="detail-label">Type</div>
                                <div class="detail-value">${leak.type}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Severity</div>
                                <div class="detail-value">${leak.severity}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Size</div>
                                <div class="detail-value">${leak.size_formatted} bytes</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Count</div>
                                <div class="detail-value">${leak.count}</div>
                            </div>
                        </div>
                        <div class="detail-item" style="margin-bottom: 15px;">
                            <div class="detail-label">Location</div>
                            <div class="detail-value">${leak.location}</div>
                        </div>
                        ${leak.message ? `
                        <div class="detail-item" style="margin-bottom: 15px;">
                            <div class="detail-label">Message</div>
                            <div class="detail-value">${leak.message}</div>
                        </div>
                        ` : ''}
                        ${leak.stack_trace.length > 0 ? `
                        <div>
                            <div class="detail-label" style="margin-bottom: 10px;">Stack Trace</div>
                            <div class="stack-trace">
                                ${leak.stack_trace.map((frame, i) => `<div class="stack-frame">#${i}: ${frame}</div>`).join('')}
                            </div>
                        </div>
                        ` : ''}
                    </div>
                `;
                container.appendChild(leakDiv);
            });
        }

        function toggleLeak(index) {
            const details = document.getElementById(`details-${index}`);
            const icon = document.getElementById(`icon-${index}`);
            
            if (details.classList.contains('active')) {
                details.classList.remove('active');
                icon.classList.remove('rotated');
            } else {
                details.classList.add('active');
                icon.classList.add('rotated');
            }
        }

        // Filtering functionality
        let allLeaks = [];
        let filteredLeaks = [];

        function initializeFilters() {
            allLeaks = [...leaks];
            filteredLeaks = [...leaks];
            
            // Add event listeners to filter inputs
            document.getElementById('search-input').addEventListener('input', applyFilters);
            document.getElementById('file-filter').addEventListener('input', applyFilters);
            document.getElementById('function-filter').addEventListener('input', applyFilters);
            document.getElementById('severity-filter').addEventListener('change', applyFilters);
        }

        function applyFilters() {
            const searchTerm = document.getElementById('search-input').value.toLowerCase();
            const fileFilter = document.getElementById('file-filter').value.toLowerCase();
            const functionFilter = document.getElementById('function-filter').value.toLowerCase();
            const severityFilter = document.getElementById('severity-filter').value;

            filteredLeaks = allLeaks.filter(leak => {
                // Search filter
                if (searchTerm && !matchesSearch(leak, searchTerm)) {
                    return false;
                }

                // File filter
                if (fileFilter && !leak.stack_trace.some(frame => 
                    frame.toLowerCase().includes(fileFilter))) {
                    return false;
                }

                // Function filter
                if (functionFilter && !leak.stack_trace.some(frame => 
                    frame.toLowerCase().includes(functionFilter))) {
                    return false;
                }

                // Severity filter
                if (severityFilter && leak.severity !== severityFilter) {
                    return false;
                }

                return true;
            });

            updateLeakVisibility();
            updateCounts();
        }

        function matchesSearch(leak, searchTerm) {
            return (
                leak.type.toLowerCase().includes(searchTerm) ||
                leak.location.toLowerCase().includes(searchTerm) ||
                leak.message.toLowerCase().includes(searchTerm) ||
                leak.stack_trace.some(frame => frame.toLowerCase().includes(searchTerm))
            );
        }

        function updateLeakVisibility() {
            const leakItems = document.querySelectorAll('.leak-item');
            
            leakItems.forEach((item, index) => {
                const isVisible = filteredLeaks.some(leak => leak.id === index);
                item.classList.toggle('hidden', !isVisible);
            });
        }

        function updateCounts() {
            document.getElementById('visible-count').textContent = filteredLeaks.length;
            document.getElementById('total-count').textContent = allLeaks.length;
        }

        function clearFilters() {
            document.getElementById('search-input').value = '';
            document.getElementById('file-filter').value = '';
            document.getElementById('function-filter').value = '';
            document.getElementById('severity-filter').value = '';
            
            filteredLeaks = [...allLeaks];
            updateLeakVisibility();
            updateCounts();
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            generateLeaksHTML();
            initializeFilters();
        });
    </script>
</body>
</html>''' 