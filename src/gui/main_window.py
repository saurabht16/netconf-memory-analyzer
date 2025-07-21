"""
Main GUI window for Memory Leak Analyzer
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from typing import Optional, List
import threading

from ..models.leak_data import LeakDatabase, MemoryLeak, LeakType
from ..parsers.valgrind_parser import ValgrindParser
from ..parsers.asan_parser import AsanParser
from ..reports.html_generator import HTMLGenerator


class MemoryLeakGUI:
    """Main GUI application for Memory Leak Analyzer"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Memory Leak Analyzer")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Data
        self.leak_db = LeakDatabase()
        self.filtered_db = LeakDatabase()  # For storing filtered results
        self.current_file = None
        self.is_filtered = False
        
        # Parsers
        self.valgrind_parser = ValgrindParser()
        self.asan_parser = AsanParser()
        self.html_generator = HTMLGenerator()
        
        # GUI components
        self.setup_styles()
        self.create_widgets()
        self.create_menu()
        
    def setup_styles(self):
        """Setup custom styles for the GUI"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure custom styles
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 10, 'bold'))
        style.configure('Error.TLabel', foreground='red')
        style.configure('Success.TLabel', foreground='green')
        
    def create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Valgrind XML...", command=self.open_valgrind_file)
        file_menu.add_command(label="Open ASan Log...", command=self.open_asan_file)
        file_menu.add_separator()
        file_menu.add_command(label="Export HTML Report...", command=self.export_html_report)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self.refresh_display)
        view_menu.add_command(label="Clear All", command=self.clear_all)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_widgets(self):
        """Create the main GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=2)
        main_frame.columnconfigure(1, weight=1) 
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Memory Leak Analyzer", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # File operations frame
        file_frame = ttk.LabelFrame(main_frame, text="File Operations", padding="10")
        file_frame.grid(row=1, column=0, columnspan=1, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(2, weight=1)
        
        # File operation buttons
        ttk.Button(file_frame, text="Open Valgrind XML", 
                  command=self.open_valgrind_file).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(file_frame, text="Open ASan Log", 
                  command=self.open_asan_file).grid(row=0, column=1, padx=5)
        
        # Current file label
        self.file_label = ttk.Label(file_frame, text="No file loaded")
        self.file_label.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=(10, 0))
        
        # Filter/Search frame
        filter_frame = ttk.LabelFrame(main_frame, text="Search & Filter", padding="10")
        filter_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        filter_frame.columnconfigure(1, weight=1)
        
        # Search box
        ttk.Label(filter_frame, text="Search:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        self.search_entry.bind('<KeyRelease>', self.on_search_change)
        
        # Filter options
        ttk.Label(filter_frame, text="File:").grid(row=1, column=0, sticky=tk.W, pady=(0, 2))
        self.filter_file_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.filter_file_var, width=15).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 2))
        
        ttk.Label(filter_frame, text="Function:").grid(row=2, column=0, sticky=tk.W, pady=(0, 2))
        self.filter_func_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.filter_func_var, width=15).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 2))
        
        ttk.Label(filter_frame, text="Severity:").grid(row=3, column=0, sticky=tk.W, pady=(0, 2))
        self.filter_severity_var = tk.StringVar()
        severity_combo = ttk.Combobox(filter_frame, textvariable=self.filter_severity_var, 
                                    values=['All', 'HIGH', 'MEDIUM', 'LOW'], state='readonly', width=12)
        severity_combo.set('All')
        severity_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 2))
        
        # Cleanup options
        ttk.Label(filter_frame, text="Cleanup:").grid(row=4, column=0, sticky=tk.W, pady=(5, 2))
        cleanup_frame = ttk.Frame(filter_frame)
        cleanup_frame.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=(5, 2))
        
        self.cleanup_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(cleanup_frame, text="Enable", variable=self.cleanup_enabled_var).grid(row=0, column=0, sticky=tk.W)
        
        self.remove_system_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cleanup_frame, text="System libs", variable=self.remove_system_var).grid(row=0, column=1, sticky=tk.W)
        
        self.remove_small_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cleanup_frame, text="Small leaks", variable=self.remove_small_var).grid(row=0, column=2, sticky=tk.W)
        
        # Filter buttons
        filter_buttons_frame = ttk.Frame(filter_frame)
        filter_buttons_frame.grid(row=5, column=0, columnspan=2, pady=(5, 0))
        
        ttk.Button(filter_buttons_frame, text="Apply Filter", 
                  command=self.apply_filters).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(filter_buttons_frame, text="Clear", 
                  command=self.clear_filters).grid(row=0, column=1)
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        stats_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        # Statistics labels
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=6, width=30)
        self.stats_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.rowconfigure(0, weight=1)
        
        # Main content area
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Create notebook for different views
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Leaks list tab
        self.create_leaks_tab()
        
        # Details tab
        self.create_details_tab()
        
        # Summary tab
        self.create_summary_tab()
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                          mode='determinate')
        self.progress_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        self.progress_bar.grid_remove()  # Hide initially
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def create_leaks_tab(self):
        """Create the leaks list tab"""
        leaks_frame = ttk.Frame(self.notebook)
        self.notebook.add(leaks_frame, text="Memory Leaks")
        
        # Create treeview for leaks
        columns = ('Type', 'Severity', 'Size', 'Count', 'Location')
        self.leaks_tree = ttk.Treeview(leaks_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        self.leaks_tree.heading('Type', text='Leak Type')
        self.leaks_tree.heading('Severity', text='Severity')
        self.leaks_tree.heading('Size', text='Size (bytes)')
        self.leaks_tree.heading('Count', text='Count')
        self.leaks_tree.heading('Location', text='Location')
        
        self.leaks_tree.column('Type', width=150)
        self.leaks_tree.column('Severity', width=100)
        self.leaks_tree.column('Size', width=100)
        self.leaks_tree.column('Count', width=80)
        self.leaks_tree.column('Location', width=400)
        
        # Scrollbars for treeview
        tree_scroll_y = ttk.Scrollbar(leaks_frame, orient=tk.VERTICAL, command=self.leaks_tree.yview)
        tree_scroll_x = ttk.Scrollbar(leaks_frame, orient=tk.HORIZONTAL, command=self.leaks_tree.xview)
        self.leaks_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        # Grid layout
        self.leaks_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        tree_scroll_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        leaks_frame.columnconfigure(0, weight=1)
        leaks_frame.rowconfigure(0, weight=1)
        
        # Bind selection event
        self.leaks_tree.bind('<<TreeviewSelect>>', self.on_leak_select)
    
    def create_details_tab(self):
        """Create the leak details tab"""
        details_frame = ttk.Frame(self.notebook)
        self.notebook.add(details_frame, text="Details")
        
        # Details text area
        self.details_text = scrolledtext.ScrolledText(details_frame, wrap=tk.WORD)
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)
    
    def create_summary_tab(self):
        """Create the summary tab"""
        summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(summary_frame, text="Summary")
        
        # Summary text area
        self.summary_text = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD)
        self.summary_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.rowconfigure(0, weight=1)
    
    def open_valgrind_file(self):
        """Open and parse a Valgrind XML file"""
        file_path = filedialog.askopenfilename(
            title="Select Valgrind XML file",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if file_path:
            self.load_file(file_path, 'valgrind')
    
    def open_asan_file(self):
        """Open and parse an ASan log file"""
        file_path = filedialog.askopenfilename(
            title="Select ASan log file",
            filetypes=[("Log files", "*.log *.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            self.load_file(file_path, 'asan')
    
    def load_file(self, file_path: str, file_type: str):
        """Load and parse a file in a separate thread"""
        self.current_file = Path(file_path)
        self.file_label.config(text=f"Loading: {self.current_file.name}")
        self.status_var.set("Loading file...")
        self.progress_bar.grid()
        self.progress_var.set(0)
        
        # Start parsing in a separate thread
        thread = threading.Thread(target=self._parse_file_thread, args=(file_path, file_type))
        thread.daemon = True
        thread.start()
    
    def _parse_file_thread(self, file_path: str, file_type: str):
        """Parse file in a separate thread"""
        try:
            self.root.after(0, lambda: self.progress_var.set(25))
            
            # Clear existing data
            self.leak_db.clear()
            
            # Parse the file
            file_path_obj = Path(file_path)
            
            if file_type == 'valgrind':
                if not self.valgrind_parser.validate_file(file_path_obj):
                    raise ValueError("Invalid Valgrind XML file")
                leaks = self.valgrind_parser.parse_file(file_path_obj)
            else:
                if not self.asan_parser.validate_file(file_path_obj):
                    raise ValueError("Invalid ASan log file")
                leaks = self.asan_parser.parse_file(file_path_obj)
            
            self.root.after(0, lambda: self.progress_var.set(75))
            
            # Add leaks to database
            self.leak_db.add_leaks(leaks)
            
            self.root.after(0, lambda: self.progress_var.set(100))
            
            # Update GUI on main thread
            self.root.after(0, self._update_gui_after_load)
            
        except Exception as e:
            self.root.after(0, lambda: self._show_error(f"Error loading file: {str(e)}"))
    
    def _update_gui_after_load(self):
        """Update GUI after file is loaded"""
        self.file_label.config(text=f"Loaded: {self.current_file.name}")
        self.status_var.set(f"Loaded {len(self.leak_db.get_all_leaks())} leaks")
        self.progress_bar.grid_remove()
        
        self.refresh_display()
    
    def _show_error(self, message: str):
        """Show error message"""
        self.file_label.config(text="Error loading file")
        self.status_var.set("Error")
        self.progress_bar.grid_remove()
        messagebox.showerror("Error", message)
    
    def on_search_change(self, event):
        """Handle real-time search as user types"""
        search_term = self.search_var.get().strip()
        if len(search_term) >= 2:  # Start searching after 2 characters
            self.apply_search(search_term)
        elif len(search_term) == 0:
            self.clear_filters()
    
    def apply_search(self, search_term):
        """Apply search to current leaks"""
        if not self.leak_db.get_all_leaks():
            return
        
        filtered_leaks = self.leak_db.search_leaks(search_term)
        self.filtered_db.clear()
        self.filtered_db.add_leaks(filtered_leaks)
        self.is_filtered = True
        self.refresh_display()
        self.status_var.set(f"Search: {len(filtered_leaks)} of {len(self.leak_db.get_all_leaks())} leaks match '{search_term}'")
    
    def apply_filters(self):
        """Apply all filters and cleanup to the leak database"""
        if not self.leak_db.get_all_leaks():
            return
        
        # Start with original leaks
        base_leaks = self.leak_db.get_all_leaks()
        
        # Apply cleanup first if enabled
        if self.cleanup_enabled_var.get():
            temp_db = LeakDatabase()
            temp_db.add_leaks(base_leaks)
            
            cleaned_leaks = temp_db.cleanup_leaks(
                remove_system_libs=self.remove_system_var.get(),
                remove_third_party=True,  # Always remove third-party by default
                min_leak_size=8 if self.remove_small_var.get() else 1,
                remove_incomplete_traces=True,
                remove_reachable=False  # Keep reachable by default in GUI
            )
            
            cleanup_stats = temp_db.get_cleanup_stats(cleaned_leaks)
            base_leaks = cleaned_leaks
            
            # Show cleanup stats
            cleanup_msg = (f"Cleanup: {cleanup_stats['removed_count']} removed "
                          f"({cleanup_stats['removal_percentage']:.1f}%), "
                          f"{cleanup_stats['cleaned_count']} remaining")
        else:
            cleanup_msg = ""
        
        # Get filter values
        file_pattern = self.filter_file_var.get().strip()
        func_pattern = self.filter_func_var.get().strip()
        severity = self.filter_severity_var.get()
        search_term = self.search_var.get().strip()
        
        # Apply search if specified
        if search_term:
            temp_db = LeakDatabase()
            temp_db.add_leaks(base_leaks)
            base_leaks = temp_db.search_leaks(search_term)
        
        # Apply other filters
        severities = [severity] if severity and severity != 'All' else None
        
        # Create temporary database for filtering
        temp_db = LeakDatabase()
        temp_db.add_leaks(base_leaks)
        
        filtered_leaks = temp_db.filter_leaks(
            file_pattern=file_pattern if file_pattern else None,
            function_pattern=func_pattern if func_pattern else None,
            severities=severities
        )
        
        # Update filtered database
        self.filtered_db.clear()
        self.filtered_db.add_leaks(filtered_leaks)
        self.is_filtered = True
        self.refresh_display()
        
        # Update status
        total_leaks = len(self.leak_db.get_all_leaks())
        filtered_count = len(filtered_leaks)
        status_msg = f"Applied: {filtered_count} of {total_leaks} leaks shown"
        if cleanup_msg:
            status_msg = cleanup_msg + " | " + status_msg
        self.status_var.set(status_msg)
    
    def clear_filters(self):
        """Clear all filters and cleanup, show all leaks"""
        self.search_var.set("")
        self.filter_file_var.set("")
        self.filter_func_var.set("")
        self.filter_severity_var.set("All")
        self.cleanup_enabled_var.set(False)
        self.remove_system_var.set(True)
        self.remove_small_var.set(True)
        self.filtered_db.clear()
        self.is_filtered = False
        self.refresh_display()
        self.status_var.set(f"Showing all {len(self.leak_db.get_all_leaks())} leaks")
    
    def get_current_leaks(self):
        """Get currently displayed leaks (filtered or all)"""
        if self.is_filtered:
            return self.filtered_db.get_all_leaks()
        else:
            return self.leak_db.get_all_leaks()
    
    def get_current_db(self):
        """Get current database (filtered or original)"""
        if self.is_filtered:
            return self.filtered_db
        else:
            return self.leak_db
    
    def refresh_display(self):
        """Refresh all display components"""
        self.update_leaks_tree()
        self.update_statistics()
        self.update_summary()
        self.details_text.delete(1.0, tk.END)
    
    def update_leaks_tree(self):
        """Update the leaks treeview"""
        # Clear existing items
        for item in self.leaks_tree.get_children():
            self.leaks_tree.delete(item)
        
        # Add leaks (use current filtered or all leaks)
        current_leaks = self.get_current_leaks()
        for i, leak in enumerate(current_leaks):
            self.leaks_tree.insert('', 'end', values=(
                leak.leak_type.value.replace('_', ' ').title(),
                leak.get_severity(),
                f"{leak.size:,}",
                leak.count,
                leak.primary_location
            ), tags=(str(i),))
    
    def update_statistics(self):
        """Update the statistics display"""
        self.stats_text.delete(1.0, tk.END)
        
        current_db = self.get_current_db()
        stats = current_db.get_statistics()
        
        text = f"{'Filtered' if self.is_filtered else 'Total'} Leaks: {stats['total_leaks']}\n"
        text += f"Total Bytes: {stats['total_bytes']:,}\n"
        
        if self.is_filtered:
            text += f"(Original total: {len(self.leak_db.get_all_leaks())})\n"
        
        text += "\nBy Severity:\n"
        for severity, count in stats['by_severity'].items():
            text += f"  {severity}: {count}\n"
        
        text += "\nBy Type:\n"
        for leak_type, info in stats['by_type'].items():
            text += f"  {leak_type.replace('_', ' ').title()}: {info['count']}\n"
        
        self.stats_text.insert(1.0, text)
    
    def update_summary(self):
        """Update the summary tab"""
        self.summary_text.delete(1.0, tk.END)
        
        current_db = self.get_current_db()
        stats = current_db.get_statistics()
        
        summary = "MEMORY LEAK ANALYSIS SUMMARY\n"
        summary += "=" * 40 + "\n\n"
        
        if self.current_file:
            summary += f"File: {self.current_file}\n"
            all_leaks = self.leak_db.get_all_leaks()
            summary += f"Analysis Date: {all_leaks[0].timestamp if all_leaks else 'N/A'}\n\n"
        
        if self.is_filtered:
            summary += f"FILTERED RESULTS ({stats['total_leaks']} of {len(self.leak_db.get_all_leaks())} issues shown)\n"
            summary += "-" * 50 + "\n"
        
        summary += f"Issues Found: {stats['total_leaks']}\n"
        summary += f"Total Memory Affected: {stats['total_bytes']:,} bytes\n\n"
        
        summary += "SEVERITY BREAKDOWN:\n"
        summary += "-" * 20 + "\n"
        for severity, count in stats['by_severity'].items():
            summary += f"{severity}: {count} issues\n"
        
        summary += "\nLEAK TYPE BREAKDOWN:\n"
        summary += "-" * 20 + "\n"
        for leak_type, info in stats['by_type'].items():
            summary += f"{leak_type.replace('_', ' ').title()}: {info['count']} issues ({info['bytes']:,} bytes)\n"
        
        if stats['top_locations']:
            summary += "\nTOP PROBLEM LOCATIONS:\n"
            summary += "-" * 25 + "\n"
            for location, count in stats['top_locations'][:5]:
                summary += f"{count}x: {location}\n"
        
        self.summary_text.insert(1.0, summary)
    
    def on_leak_select(self, event):
        """Handle leak selection in treeview"""
        selection = self.leaks_tree.selection()
        if selection:
            item = self.leaks_tree.item(selection[0])
            leak_index = int(item['tags'][0])
            current_leaks = self.get_current_leaks()
            if leak_index < len(current_leaks):
                leak = current_leaks[leak_index]
                self.show_leak_details(leak)
    
    def show_leak_details(self, leak: MemoryLeak):
        """Show detailed information about a leak"""
        self.details_text.delete(1.0, tk.END)
        
        details = f"LEAK DETAILS\n"
        details += "=" * 20 + "\n\n"
        details += f"Type: {leak.leak_type.value.replace('_', ' ').title()}\n"
        details += f"Severity: {leak.get_severity()}\n"
        details += f"Size: {leak.size:,} bytes\n"
        details += f"Count: {leak.count}\n"
        details += f"Location: {leak.primary_location}\n\n"
        
        if leak.message:
            details += f"Message: {leak.message}\n\n"
        
        if leak.stack_trace:
            details += "STACK TRACE:\n"
            details += "-" * 15 + "\n"
            for i, frame in enumerate(leak.stack_trace):
                details += f"#{i}: {frame}\n"
        
        self.details_text.insert(1.0, details)
    
    def export_html_report(self):
        """Export HTML report"""
        current_db = self.get_current_db()
        if not current_db.get_all_leaks():
            messagebox.showwarning("Warning", "No leaks to export. Please load a file first.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save HTML Report",
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.html_generator.generate_report(current_db, Path(file_path))
                report_type = "filtered " if self.is_filtered else ""
                messagebox.showinfo("Success", f"HTML {report_type}report saved to: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save HTML report: {str(e)}")
    
    def clear_all(self):
        """Clear all data"""
        self.leak_db.clear()
        self.filtered_db.clear()
        self.current_file = None
        self.is_filtered = False
        self.clear_filters()
        self.file_label.config(text="No file loaded")
        self.status_var.set("Ready")
        self.refresh_display()
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Memory Leak Analyzer v1.0

A tool for analyzing memory leaks from:
- Valgrind XML output files
- AddressSanitizer (ASan) log files

Features:
- Parse and display memory leaks
- Generate HTML reports
- Filter by severity and type
- Detailed stack trace analysis

Created with Python and Tkinter"""
        
        messagebox.showinfo("About", about_text)
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop() 